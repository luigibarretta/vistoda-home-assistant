"""Authenticated WebSocket commands for user-defined recording lists."""

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .errors import BridgeError
from .recording_list_model import RecordingListError
from .ring_access import require_ring_access
from .ring_recording_lists import async_get_recording_lists


@callback
def async_register(hass: HomeAssistant) -> None:
    """Register bounded list mutation commands."""
    websocket_api.async_register_command(hass, ws_ring_recording_list_create)
    websocket_api.async_register_command(hass, ws_ring_recording_list_update)
    websocket_api.async_register_command(hass, ws_ring_recording_list_delete)
    websocket_api.async_register_command(hass, ws_ring_recording_list_membership)


def _resolve(hass: HomeAssistant, entry_id: str):
    from .websocket import resolve_ring

    return resolve_ring(hass, entry_id)


def _validation_error(connection, message_id: int, error: RecordingListError) -> None:
    labels = {
        "invalid_name": "List name is invalid",
        "duplicate_name": "A list with this name already exists",
        "list_limit": "Recording list limit reached",
        "list_not_found": "Recording list was not found",
        "invalid_recording": "Recording identifier is invalid",
        "membership_limit": "Recording list membership limit reached",
    }
    connection.send_error(message_id, error.code, labels.get(error.code, "Invalid list request"))


@websocket_api.websocket_command(
    {
        vol.Required("type"): "media_bridge/ring/recording_lists/create",
        vol.Required("entry_id"): str,
        vol.Required("name"): vol.All(str, vol.Length(min=1, max=64)),
    }
)
@websocket_api.async_response
@require_ring_access("control")
async def ws_ring_recording_list_create(hass, connection, msg: dict[str, Any]) -> None:
    """Create a list shared by every authenticated Home Assistant client."""
    if _resolve(hass, msg["entry_id"]) is None:
        connection.send_error(msg["id"], "not_found", "Ring bridge is not loaded")
        return
    try:
        lists, list_id = await async_get_recording_lists(hass).async_create(
            msg["entry_id"], msg["name"]
        )
    except RecordingListError as error:
        _validation_error(connection, msg["id"], error)
        return
    connection.send_result(msg["id"], {"lists": lists, "created_list_id": list_id})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "media_bridge/ring/recording_lists/update",
        vol.Required("entry_id"): str,
        vol.Required("list_id"): vol.All(str, vol.Length(min=1, max=64)),
        vol.Required("name"): vol.All(str, vol.Length(min=1, max=64)),
    }
)
@websocket_api.async_response
@require_ring_access("control")
async def ws_ring_recording_list_update(hass, connection, msg: dict[str, Any]) -> None:
    """Rename one list without changing its recording memberships."""
    if _resolve(hass, msg["entry_id"]) is None:
        connection.send_error(msg["id"], "not_found", "Ring bridge is not loaded")
        return
    try:
        lists = await async_get_recording_lists(hass).async_update(
            msg["entry_id"], msg["list_id"], msg["name"]
        )
    except RecordingListError as error:
        _validation_error(connection, msg["id"], error)
        return
    connection.send_result(msg["id"], {"lists": lists})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "media_bridge/ring/recording_lists/delete",
        vol.Required("entry_id"): str,
        vol.Required("list_id"): vol.All(str, vol.Length(min=1, max=64)),
    }
)
@websocket_api.async_response
@require_ring_access("control")
async def ws_ring_recording_list_delete(hass, connection, msg: dict[str, Any]) -> None:
    """Delete only a list; recordings remain untouched."""
    if _resolve(hass, msg["entry_id"]) is None:
        connection.send_error(msg["id"], "not_found", "Ring bridge is not loaded")
        return
    lists, deleted = await async_get_recording_lists(hass).async_delete(
        msg["entry_id"], msg["list_id"]
    )
    connection.send_result(msg["id"], {"lists": lists, "deleted": deleted})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "media_bridge/ring/recording_lists/set_membership",
        vol.Required("entry_id"): str,
        vol.Required("list_id"): vol.All(str, vol.Length(min=1, max=64)),
        vol.Required("recording_id"): vol.All(str, vol.Length(min=1, max=64)),
        vol.Required("included"): bool,
    }
)
@websocket_api.async_response
@require_ring_access("control")
async def ws_ring_recording_list_membership(hass, connection, msg: dict[str, Any]) -> None:
    """Add or remove one extant recording from one list."""
    resolved = _resolve(hass, msg["entry_id"])
    if resolved is None:
        connection.send_error(msg["id"], "not_found", "Ring bridge is not loaded")
        return
    runtime, alias = resolved
    if msg["included"]:
        try:
            recordings = await runtime.client.ring_recordings(alias)
        except BridgeError:
            connection.send_error(msg["id"], "unavailable", "Ring archive is unavailable")
            return
        if not any(item.recording_id == msg["recording_id"] for item in recordings):
            connection.send_error(msg["id"], "not_found", "Recording was not found")
            return
    try:
        lists = await async_get_recording_lists(hass).async_set_membership(
            msg["entry_id"], msg["list_id"], msg["recording_id"], msg["included"]
        )
    except RecordingListError as error:
        _validation_error(connection, msg["id"], error)
        return
    connection.send_result(msg["id"], {"lists": lists})
