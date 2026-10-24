"""Verified EZVIZ settings from the source the user chose for each entry.

Standalone entries (the default) use the Vistoda EZVIZ app. Entries delegated to
Home Assistant's EZVIZ integration show that integration's own entities in the
panel; the one setting Vistoda adds, camera arming, goes through the official
camera entity's motion-detection services and is confirmed by its published state.
"""

import asyncio
import logging
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_track_state_change_event

from .const import CONF_PROVIDER, PROVIDER_EZVIZ
from .ezviz_controls_websocket import async_app_info, async_app_set, ws_ptz
from .ezviz_core import UNAVAILABLE, native_camera

_LOGGER = logging.getLogger(__name__)
ENTRY_ID = vol.All(str, vol.Length(min=1, max=64))
KEY = vol.All(str, vol.Length(min=1, max=64))
# Integers are only valid for the app's sensitivity range.
VALUE = vol.Any(bool, int, str)
DEFENCE = "camera_defence"
# The official coordinator debounces refresh requests for up to ten seconds.
CONFIRM_TIMEOUT = 20


def _defence(state) -> bool | None:
    """Camera arming as the official camera entity publishes it, else unknown."""
    if state is None or state.state == UNAVAILABLE:
        return None
    return bool(state.attributes.get("motion_detection", False))


def _settings(state) -> list[dict]:
    value = _defence(state)
    if value is None:
        return []
    return [{"key": DEFENCE, "group": "arming", "kind": "boolean", "value": value}]


def _resolve(hass: HomeAssistant, entry_id: str):
    """Return the official camera entity's state for a delegated entry, else None."""
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None or entry.data.get(CONF_PROVIDER) != PROVIDER_EZVIZ:
        return None
    return native_camera(hass, entry)


def _native_unavailable(connection, msg_id) -> None:
    connection.send_error(
        msg_id, "native_unavailable", "The official EZVIZ integration is unavailable"
    )


async def _confirm(hass: HomeAssistant, entity_id: str, value: bool) -> bool:
    """Ask the official entity for a fresh poll and wait until it shows the value."""
    shown = asyncio.Event()

    @callback
    def _changed(_event) -> None:
        if _defence(hass.states.get(entity_id)) is value:
            shown.set()

    unsubscribe = async_track_state_change_event(hass, [entity_id], _changed)
    try:
        await hass.services.async_call(
            "homeassistant", "update_entity", {"entity_id": entity_id}, blocking=True
        )
        if _defence(hass.states.get(entity_id)) is value:
            return True
        async with asyncio.timeout(CONFIRM_TIMEOUT):
            await shown.wait()
        return True
    except (HomeAssistantError, TimeoutError):
        return False
    finally:
        unsubscribe()


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
    state = _resolve(hass, msg["entry_id"])
    if state is None:
        _native_unavailable(connection, msg["id"])
        return
    connection.send_result(msg["id"], {"settings": _settings(state), "source": "native"})


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
    if msg["key"] != DEFENCE:
        # Every other delegated control is an official entity the panel lists itself.
        connection.send_error(msg["id"], "not_supported", "Use the official EZVIZ entity")
        return
    value, expected = msg["value"], msg["expected_value"]
    if not isinstance(value, bool) or not isinstance(expected, bool):
        connection.send_error(msg["id"], "invalid_format", "Unsupported EZVIZ setting value")
        return
    state = _resolve(hass, msg["entry_id"])
    if state is None:
        _native_unavailable(connection, msg["id"])
        return
    current = _defence(state)
    if current is None:
        connection.send_error(msg["id"], "unavailable", "The EZVIZ camera is offline")
        return
    if current != expected:
        connection.send_error(msg["id"], "conflict", "EZVIZ setting changed upstream")
        return
    if value != current:
        service = "enable_motion_detection" if value else "disable_motion_detection"
        try:
            await hass.services.async_call(
                "camera",
                service,
                {"entity_id": state.entity_id},
                blocking=True,
                context=connection.context(msg),
            )
        except Exception:  # The official service may raise its client library's own errors.
            _LOGGER.debug(
                "Official EZVIZ %s failed for %s", service, state.entity_id, exc_info=True
            )
            connection.send_error(msg["id"], "unavailable", "EZVIZ rejected the setting")
            return
        if not await _confirm(hass, state.entity_id, value):
            # Never undo blind: the write may still have reached the camera.
            connection.send_error(msg["id"], "unconfirmed", "EZVIZ did not confirm the setting")
            return
    settings = _settings(hass.states.get(state.entity_id))
    connection.send_result(msg["id"], {"settings": settings, "source": "native"})
