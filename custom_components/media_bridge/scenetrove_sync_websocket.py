"""Panel commands for the SceneTrove cloud microSD sync schedule (ADR 0029).

Anyone who may see the camera reads the schedule and the last run; only Home
Assistant administrators change it. SceneTrove validates again and remains the
single owner of the value.
"""

import logging
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_PROVIDER, PROVIDER_EZVIZ
from .ring_access import can_access_ezviz_entry
from .scenetrove_sync import (
    SceneTroveSyncClient,
    SceneTroveSyncError,
    sync_target,
    valid_schedule,
)

_LOGGER = logging.getLogger(__name__)
ENTRY_ID = vol.All(str, vol.Length(min=1, max=64))


@callback
def async_register(hass: HomeAssistant) -> None:
    websocket_api.async_register_command(hass, ws_sd_sync_info)
    websocket_api.async_register_command(hass, ws_sd_sync_set)


def _client(hass: HomeAssistant, entry_id: str) -> SceneTroveSyncClient | None:
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None or entry.data.get(CONF_PROVIDER) != PROVIDER_EZVIZ:
        return None
    target = sync_target(entry.options)
    if target is None:
        return None
    return SceneTroveSyncClient(async_get_clientsession(hass), *target)


def _failed(connection, msg_id, error: SceneTroveSyncError) -> None:
    connection.send_error(msg_id, error.code, "SceneTrove microSD sync request failed")


@websocket_api.websocket_command(
    {vol.Required("type"): "media_bridge/ezviz/sd_sync/info", vol.Required("entry_id"): ENTRY_ID}
)
@websocket_api.async_response
async def ws_sd_sync_info(hass, connection, msg: dict[str, Any]) -> None:
    if not can_access_ezviz_entry(hass, connection.user, msg["entry_id"]):
        connection.send_error(msg["id"], "unauthorized", "EZVIZ access is not permitted")
        return
    client = _client(hass, msg["entry_id"])
    if client is None:
        # Not an error: the panel shows how to link SceneTrove instead.
        connection.send_result(msg["id"], {"sync": None})
        return
    try:
        sync = await client.status()
    except SceneTroveSyncError as error:
        _failed(connection, msg["id"], error)
        return
    connection.send_result(msg["id"], {"sync": sync})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "media_bridge/ezviz/sd_sync/set",
        vol.Required("entry_id"): ENTRY_ID,
        vol.Required("enabled"): bool,
        vol.Required("interval_minutes"): int,
    }
)
@websocket_api.async_response
async def ws_sd_sync_set(hass, connection, msg: dict[str, Any]) -> None:
    if not connection.user.is_admin:
        connection.send_error(msg["id"], "unauthorized", "Administrator access required")
        return
    if not valid_schedule(msg["enabled"], msg["interval_minutes"]):
        connection.send_error(msg["id"], "invalid_format", "Unsupported microSD sync interval")
        return
    client = _client(hass, msg["entry_id"])
    if client is None:
        connection.send_error(msg["id"], "scenetrove_not_linked", "SceneTrove is not linked")
        return
    try:
        sync = await client.set_schedule(msg["enabled"], msg["interval_minutes"])
    except SceneTroveSyncError as error:
        _failed(connection, msg["id"], error)
        return
    # Audit trail on the Vistoda side; SceneTrove logs the change as well.
    _LOGGER.info(
        "SceneTrove microSD sync for entry %s changed by user %s: enabled=%s, every %s min",
        msg["entry_id"],
        connection.user.id,
        sync["enabled"],
        sync["interval_minutes"],
    )
    connection.send_result(msg["id"], {"sync": sync})
