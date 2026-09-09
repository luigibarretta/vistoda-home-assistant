"""Authenticated HA boundary for standalone provider video recordings."""

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from . import BridgeRuntime
from .const import CONF_ALIAS, CONF_PROVIDER, DOMAIN, PROVIDER_EZVIZ
from .errors import BridgeError, EnrollmentBusyError, RateLimitedError

ENTRY_ID = vol.All(str, vol.Length(min=1, max=64))
RECORDING_ID = vol.All(str, vol.Match(r"^[0-9a-f-]{36}$"))
REQUEST_ID = vol.All(str, vol.Match(r"^[0-9a-f-]{36}$"))


@callback
def async_register(hass: HomeAssistant) -> None:
    """Register the archive commands once."""
    websocket_api.async_register_command(hass, ws_list_recordings)
    websocket_api.async_register_command(hass, ws_create_recording)
    websocket_api.async_register_command(hass, ws_delete_recording)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "media_bridge/ezviz/recordings/list",
        vol.Required("entry_id"): ENTRY_ID,
    }
)
@websocket_api.async_response
async def ws_list_recordings(hass, connection, msg: dict[str, Any]) -> None:
    """Return redacted provider-local manifests."""
    resolved = _resolve(hass, msg["entry_id"])
    if resolved is None:
        connection.send_error(msg["id"], "not_found", "EZVIZ bridge is not loaded")
        return
    runtime, _alias = resolved
    try:
        recordings = await runtime.client.provider_recordings()
    except BridgeError:
        connection.send_error(msg["id"], "unavailable", "EZVIZ recordings are unavailable")
        return
    connection.send_result(msg["id"], {"recordings": recordings})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "media_bridge/ezviz/recordings/create",
        vol.Required("entry_id"): ENTRY_ID,
        vol.Required("duration_seconds"): vol.In((15, 30, 60)),
        vol.Required("request_id"): REQUEST_ID,
    }
)
@websocket_api.async_response
async def ws_create_recording(hass, connection, msg: dict[str, Any]) -> None:
    """Start one fixed-duration capture from the shared EZVIZ stream."""
    if not connection.user.is_admin:
        connection.send_error(msg["id"], "unauthorized", "Administrator access required")
        return
    resolved = _resolve(hass, msg["entry_id"])
    if resolved is None:
        connection.send_error(msg["id"], "not_found", "EZVIZ bridge is not loaded")
        return
    runtime, alias = resolved
    try:
        manifest = await runtime.client.create_provider_recording(
            alias,
            msg["duration_seconds"],
            msg["request_id"],
        )
    except (EnrollmentBusyError, RateLimitedError):
        connection.send_error(msg["id"], "conflict", "EZVIZ recording is already active")
        return
    except BridgeError:
        connection.send_error(msg["id"], "unavailable", "EZVIZ recording could not start")
        return
    connection.send_result(msg["id"], manifest)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "media_bridge/ezviz/recordings/delete",
        vol.Required("entry_id"): ENTRY_ID,
        vol.Required("recording_id"): RECORDING_ID,
    }
)
@websocket_api.async_response
async def ws_delete_recording(hass, connection, msg: dict[str, Any]) -> None:
    """Acknowledge and delete one completed provider-local recording."""
    if not connection.user.is_admin:
        connection.send_error(msg["id"], "unauthorized", "Administrator access required")
        return
    resolved = _resolve(hass, msg["entry_id"])
    if resolved is None:
        connection.send_error(msg["id"], "not_found", "EZVIZ bridge is not loaded")
        return
    runtime, _alias = resolved
    try:
        await runtime.client.delete_provider_recording(msg["recording_id"])
    except EnrollmentBusyError:
        connection.send_error(msg["id"], "conflict", "EZVIZ recording is still active")
        return
    except BridgeError:
        connection.send_error(msg["id"], "unavailable", "EZVIZ recording could not be deleted")
        return
    connection.send_result(msg["id"], {})


def _resolve(hass: HomeAssistant, entry_id: str) -> tuple[BridgeRuntime, str] | None:
    entry = hass.config_entries.async_get_entry(entry_id)
    runtime = hass.data.get(DOMAIN, {}).get(entry_id)
    if (
        entry is None
        or entry.data.get(CONF_PROVIDER) != PROVIDER_EZVIZ
        or not isinstance(runtime, BridgeRuntime)
        or runtime.client is None
    ):
        return None
    return runtime, entry.data[CONF_ALIAS]
