"""Verified EZVIZ settings: the Vistoda EZVIZ app first, else HA's native EZVIZ session."""

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .const import CONF_PROVIDER, PROVIDER_EZVIZ
from .ezviz_binding import CONF_EZVIZ_SOURCE_ID, valid_source_id
from .ezviz_bounded_call import bounded_call
from .ezviz_controls_websocket import async_app_info, async_app_set, ws_ptz
from .ezviz_provider_settings import (
    current_value,
    provider_value,
    settings_from_data,
    writable,
)

ENTRY_ID = vol.All(str, vol.Length(min=1, max=64))
KEY = vol.All(str, vol.Length(min=1, max=64))
# Integers are only valid for the app's sensitivity range.
VALUE = vol.Any(bool, int, str)


def _resolve(hass: HomeAssistant, entry_id: str):
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None or entry.data.get(CONF_PROVIDER) != PROVIDER_EZVIZ:
        return None
    source = entry.data.get(CONF_EZVIZ_SOURCE_ID)
    if not valid_source_id(source):
        return None
    serial = source.rsplit(":", 1)[0]
    matches = []
    for native in hass.config_entries.async_entries("ezviz"):
        coordinator = getattr(native, "runtime_data", None)
        data = getattr(coordinator, "data", None)
        if isinstance(data, dict) and isinstance(data.get(serial), dict):
            matches.append((coordinator, serial))
    return matches[0] if len(matches) == 1 else None


# The poll itself failed: the write is neither confirmed nor disproved.
POLL_FAILED = object()


async def _read_back(coordinator, serial: str, key: str) -> Any:
    """Poll the provider again; a failed or partial poll never confirms a write."""
    # async_refresh bypasses the request debouncer: a debounced refresh could
    # leave the read-back on data polled before this write.
    await coordinator.async_refresh()
    if not getattr(coordinator, "last_update_success", False):
        return POLL_FAILED
    data = coordinator.data
    camera = data.get(serial) if isinstance(data, dict) else None
    return current_value(camera, key) if isinstance(camera, dict) else None


@callback
def async_register(hass: HomeAssistant) -> None:
    websocket_api.async_register_command(hass, ws_settings_info)
    websocket_api.async_register_command(hass, ws_settings_set)
    websocket_api.async_register_command(hass, ws_ptz)


@websocket_api.websocket_command(
    {vol.Required("type"): "media_bridge/ezviz/settings/info", vol.Required("entry_id"): ENTRY_ID}
)
@websocket_api.async_response
async def ws_settings_info(hass, connection, msg: dict[str, Any]) -> None:
    if await async_app_info(hass, connection, msg):
        return
    resolved = _resolve(hass, msg["entry_id"])
    if resolved is None:
        connection.send_error(msg["id"], "unavailable", "EZVIZ settings are unavailable")
        return
    coordinator, serial = resolved
    settings = settings_from_data(coordinator.data[serial])
    connection.send_result(msg["id"], {"settings": settings, "source": "native"})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "media_bridge/ezviz/settings/set",
        vol.Required("entry_id"): ENTRY_ID,
        vol.Required("key"): KEY,
        vol.Required("value"): VALUE,
        vol.Required("expected_value"): VALUE,
    }
)
@websocket_api.async_response
async def ws_settings_set(hass, connection, msg: dict[str, Any]) -> None:
    if not connection.user.is_admin:
        connection.send_error(msg["id"], "unauthorized", "Administrator access required")
        return
    if await async_app_set(hass, connection, msg):
        return
    if not writable(msg["key"]):
        connection.send_error(msg["id"], "not_supported", "EZVIZ setting is read-only")
        return
    resolved = _resolve(hass, msg["entry_id"])
    if resolved is None:
        connection.send_error(msg["id"], "unavailable", "EZVIZ settings are unavailable")
        return
    coordinator, serial = resolved
    # pyezvizapi ships with HA's EZVIZ integration, which owns the resolved
    # coordinator; importing it here keeps Blink/Ring-only installs loadable.
    from pyezvizapi.exceptions import HTTPError, PyEzvizError

    old = current_value(coordinator.data[serial], msg["key"])
    if old != msg["expected_value"]:
        connection.send_error(msg["id"], "conflict", "EZVIZ setting changed upstream")
        return
    try:
        method_name, args = provider_value(msg["key"], msg["value"])
    except ValueError:
        connection.send_error(msg["id"], "invalid_format", "Unsupported EZVIZ setting value")
        return
    client = getattr(coordinator, "ezviz_client", None)
    try:
        await hass.async_add_executor_job(bounded_call, client, method_name, serial, *args)
        confirmed = await _read_back(coordinator, serial, msg["key"])
        if confirmed is POLL_FAILED:
            # Rolling back blind could flip a write that did succeed.
            connection.send_error(msg["id"], "unconfirmed", "EZVIZ did not confirm the setting")
            return
        if confirmed != msg["value"]:
            rollback_name, rollback_args = provider_value(msg["key"], old)
            await hass.async_add_executor_job(
                bounded_call, client, rollback_name, serial, *rollback_args
            )
            raise ValueError("read-after-write mismatch")
    except (
        AttributeError,
        HTTPError,
        KeyError,
        OSError,  # includes requests timeouts and connection errors
        PyEzvizError,
        TypeError,
        ValueError,
    ):
        # A failed call may still have reached the camera: poll again so the
        # panel's follow-up settings/info shows the provider's real state.
        await coordinator.async_refresh()
        connection.send_error(msg["id"], "unavailable", "EZVIZ rejected the setting")
        return
    settings = settings_from_data(coordinator.data[serial])
    connection.send_result(msg["id"], {"settings": settings, "source": "native"})
