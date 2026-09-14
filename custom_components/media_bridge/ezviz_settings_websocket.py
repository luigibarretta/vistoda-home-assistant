"""Verified settings boundary over Home Assistant's native EZVIZ session."""

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from pyezvizapi.exceptions import HTTPError, PyEzvizError

from .const import CONF_PROVIDER, PROVIDER_EZVIZ
from .ezviz_binding import CONF_EZVIZ_SOURCE_ID, valid_source_id
from .ezviz_provider_settings import current_value, provider_value, settings_from_data

ENTRY_ID = vol.All(str, vol.Length(min=1, max=64))
KEY = vol.All(str, vol.Length(min=1, max=64))


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


@callback
def async_register(hass: HomeAssistant) -> None:
    websocket_api.async_register_command(hass, ws_settings_info)
    websocket_api.async_register_command(hass, ws_settings_set)


@websocket_api.websocket_command(
    {vol.Required("type"): "media_bridge/ezviz/settings/info", vol.Required("entry_id"): ENTRY_ID}
)
@callback
def ws_settings_info(hass, connection, msg: dict[str, Any]) -> None:
    resolved = _resolve(hass, msg["entry_id"])
    if resolved is None:
        connection.send_error(msg["id"], "unavailable", "EZVIZ settings are unavailable")
        return
    coordinator, serial = resolved
    connection.send_result(msg["id"], {"settings": settings_from_data(coordinator.data[serial])})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "media_bridge/ezviz/settings/set",
        vol.Required("entry_id"): ENTRY_ID,
        vol.Required("key"): KEY,
        vol.Required("value"): vol.Any(bool, str),
        vol.Required("expected_value"): vol.Any(bool, str),
    }
)
@websocket_api.async_response
async def ws_settings_set(hass, connection, msg: dict[str, Any]) -> None:
    if not connection.user.is_admin:
        connection.send_error(msg["id"], "unauthorized", "Administrator access required")
        return
    resolved = _resolve(hass, msg["entry_id"])
    if resolved is None:
        connection.send_error(msg["id"], "unavailable", "EZVIZ settings are unavailable")
        return
    coordinator, serial = resolved
    old = current_value(coordinator.data[serial], msg["key"])
    if old != msg["expected_value"]:
        connection.send_error(msg["id"], "conflict", "EZVIZ setting changed upstream")
        return
    try:
        method_name, args = provider_value(msg["key"], msg["value"])
        method = getattr(coordinator.ezviz_client, method_name)
        await hass.async_add_executor_job(method, serial, *args)
        await coordinator.async_request_refresh()
        if current_value(coordinator.data[serial], msg["key"]) != msg["value"]:
            rollback_name, rollback_args = provider_value(msg["key"], old)
            await hass.async_add_executor_job(
                getattr(coordinator.ezviz_client, rollback_name), serial, *rollback_args
            )
            await coordinator.async_request_refresh()
            raise ValueError("read-after-write mismatch")
    except (AttributeError, HTTPError, PyEzvizError, TypeError, ValueError):
        connection.send_error(msg["id"], "unavailable", "EZVIZ rejected the setting")
        return
    connection.send_result(msg["id"], {"settings": settings_from_data(coordinator.data[serial])})
