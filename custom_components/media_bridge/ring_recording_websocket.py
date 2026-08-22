"""Authenticated Home Assistant WebSocket boundary for Ring recordings."""

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .errors import BridgeError


@callback
def async_register(hass: HomeAssistant) -> None:
    """Register bounded archive commands."""
    websocket_api.async_register_command(hass, ws_ring_recordings)
    websocket_api.async_register_command(hass, ws_ring_recording_start)
    websocket_api.async_register_command(hass, ws_ring_recording_status)


def _resolve(hass: HomeAssistant, entry_id: str):
    from .websocket import resolve_ring

    return resolve_ring(hass, entry_id)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "media_bridge/ring/recordings/list",
        vol.Required("entry_id"): str,
    }
)
@websocket_api.async_response
async def ws_ring_recordings(hass, connection, msg: dict[str, Any]) -> None:
    """Return archive metadata without bridge credentials or media URLs."""
    resolved = _resolve(hass, msg["entry_id"])
    if resolved is None:
        connection.send_error(msg["id"], "not_found", "Ring bridge is not loaded")
        return
    runtime, alias = resolved
    try:
        recordings = await runtime.client.ring_recordings(alias)
    except BridgeError:
        connection.send_error(msg["id"], "unavailable", "Ring archive is unavailable")
        return
    connection.send_result(
        msg["id"],
        {
            "recordings": [
                {
                    "recording_id": item.recording_id,
                    "event_at": item.event_at,
                    "bytes": item.bytes,
                }
                for item in recordings
            ]
        },
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "media_bridge/ring/recordings/import",
        vol.Required("entry_id"): str,
        vol.Required("triggered_at"): vol.All(vol.Coerce(int), vol.Range(min=1)),
    }
)
@websocket_api.async_response
async def ws_ring_recording_start(hass, connection, msg: dict[str, Any]) -> None:
    """Queue the official recording for the active browser call."""
    resolved = _resolve(hass, msg["entry_id"])
    if resolved is None:
        connection.send_error(msg["id"], "not_found", "Ring bridge is not loaded")
        return
    runtime, alias = resolved
    try:
        result = await runtime.client.import_ring_recording(alias, msg["triggered_at"])
    except BridgeError:
        connection.send_error(msg["id"], "unavailable", "Ring recording was rejected")
        return
    connection.send_result(msg["id"], _import_payload(result))


@websocket_api.websocket_command(
    {
        vol.Required("type"): "media_bridge/ring/recordings/import/status",
        vol.Required("entry_id"): str,
        vol.Required("import_id"): vol.All(str, vol.Length(min=1, max=64)),
    }
)
@websocket_api.async_response
async def ws_ring_recording_status(hass, connection, msg: dict[str, Any]) -> None:
    """Return one import job transition."""
    resolved = _resolve(hass, msg["entry_id"])
    if resolved is None:
        connection.send_error(msg["id"], "not_found", "Ring bridge is not loaded")
        return
    runtime, alias = resolved
    try:
        result = await runtime.client.ring_recording_import(alias, msg["import_id"])
    except BridgeError:
        connection.send_error(msg["id"], "unavailable", "Ring import status is unavailable")
        return
    connection.send_result(msg["id"], _import_payload(result))


def _import_payload(result) -> dict[str, str | None]:
    return {
        "import_id": result.import_id,
        "state": result.state,
        "recording_id": result.recording_id,
    }
