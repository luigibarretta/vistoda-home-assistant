"""Authenticated Home Assistant WebSocket boundary for local recordings."""

import base64
import binascii
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .errors import BridgeError


@callback
def async_register(hass: HomeAssistant) -> None:
    """Register bounded archive commands."""
    websocket_api.async_register_command(hass, ws_ring_recordings)
    websocket_api.async_register_command(hass, ws_ring_recording_upload)
    websocket_api.async_register_command(hass, ws_ring_recording_delete)
    websocket_api.async_register_command(hass, ws_ring_recordings_delete_all)


MAX_RECORDING_BYTES = 8 * 1024 * 1024
MAX_BASE64_CHARS = ((MAX_RECORDING_BYTES + 2) // 3) * 4


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
                    "started_at": item.started_at,
                    "ended_at": item.ended_at,
                    "bytes": item.bytes,
                }
                for item in recordings
            ]
        },
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "media_bridge/ring/recordings/upload",
        vol.Required("entry_id"): str,
        vol.Required("started_at"): vol.All(vol.Coerce(int), vol.Range(min=1)),
        vol.Required("ended_at"): vol.All(vol.Coerce(int), vol.Range(min=1)),
        vol.Required("media_type"): vol.All(str, vol.Length(min=9, max=64)),
        vol.Required("media_base64"): vol.All(str, vol.Length(min=4, max=MAX_BASE64_CHARS)),
    }
)
@websocket_api.async_response
async def ws_ring_recording_upload(hass, connection, msg: dict[str, Any]) -> None:
    """Commit one browser-captured call without exposing bridge credentials."""
    resolved = _resolve(hass, msg["entry_id"])
    if resolved is None:
        connection.send_error(msg["id"], "not_found", "Ring bridge is not loaded")
        return
    try:
        media = base64.b64decode(msg["media_base64"], validate=True)
    except (binascii.Error, ValueError):
        connection.send_error(msg["id"], "invalid_format", "Recording encoding is invalid")
        return
    if not 128 <= len(media) <= MAX_RECORDING_BYTES:
        connection.send_error(msg["id"], "invalid_size", "Recording size is invalid")
        return
    runtime, alias = resolved
    try:
        result = await runtime.client.upload_ring_recording(
            alias,
            msg["started_at"],
            msg["ended_at"],
            msg["media_type"],
            media,
        )
    except BridgeError:
        connection.send_error(msg["id"], "unavailable", "Local recording was rejected")
        return
    connection.send_result(
        msg["id"],
        {
            "recording_id": result.recording_id,
            "started_at": result.started_at,
            "ended_at": result.ended_at,
            "bytes": result.bytes,
            "media_type": result.media_type,
        },
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "media_bridge/ring/recordings/delete",
        vol.Required("entry_id"): str,
        vol.Required("recording_id"): vol.All(str, vol.Length(min=1, max=64)),
    }
)
@websocket_api.async_response
async def ws_ring_recording_delete(hass, connection, msg: dict[str, Any]) -> None:
    """Idempotently remove one recording through the authenticated HA boundary."""
    resolved = _resolve(hass, msg["entry_id"])
    if resolved is None:
        connection.send_error(msg["id"], "not_found", "Ring bridge is not loaded")
        return
    runtime, alias = resolved
    try:
        await runtime.client.delete_ring_recording(alias, msg["recording_id"])
    except BridgeError:
        connection.send_error(msg["id"], "unavailable", "Recording deletion failed")
        return
    connection.send_result(msg["id"], {"deleted": 1, "failed": 0})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "media_bridge/ring/recordings/delete_all",
        vol.Required("entry_id"): str,
    }
)
@websocket_api.async_response
async def ws_ring_recordings_delete_all(hass, connection, msg: dict[str, Any]) -> None:
    """Remove the complete bounded inventory and report partial failures."""
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
    deleted = 0
    failed = 0
    for recording in recordings:
        try:
            await runtime.client.delete_ring_recording(alias, recording.recording_id)
            deleted += 1
        except BridgeError:
            failed += 1
    connection.send_result(msg["id"], {"deleted": deleted, "failed": failed})
