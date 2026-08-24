"""Authenticated acknowledgement boundary for incoming Ring calls."""

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

EVENT_RING_CALL_ANSWERED = "vistoda_ring_call_answered"
CALL_ID = vol.All(str, vol.Match(r"^[A-Za-z0-9_-]{1,64}$"))


@callback
def async_register(hass: HomeAssistant) -> None:
    """Register the incoming-call acknowledgement command."""
    websocket_api.async_register_command(hass, ws_ring_call_answered)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "media_bridge/ring/call/answer",
        vol.Required("entry_id"): str,
        vol.Required("call_id"): CALL_ID,
    }
)
@callback
def ws_ring_call_answered(hass, connection, msg: dict[str, Any]) -> None:
    """Acknowledge only after an authenticated Vistoda session is active."""
    from .websocket import resolve_ring

    if resolve_ring(hass, msg["entry_id"]) is None:
        connection.send_error(msg["id"], "not_found", "Ring bridge is not loaded")
        return
    hass.bus.async_fire(EVENT_RING_CALL_ANSWERED, {"call_id": msg["call_id"]})
    connection.send_result(msg["id"], {"acknowledged": True})
