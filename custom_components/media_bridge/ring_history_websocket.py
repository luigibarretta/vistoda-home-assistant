"""Authenticated Home Assistant boundary for Ring event history."""

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback


@callback
def async_register(hass: HomeAssistant) -> None:
    websocket_api.async_register_command(hass, ws_ring_history)
    websocket_api.async_register_command(hass, ws_ring_identity_update)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "media_bridge/ring/history",
        vol.Required("entry_id"): str,
        vol.Optional("limit", default=20): vol.All(vol.Coerce(int), vol.Range(min=1, max=50)),
        vol.Optional("cursor"): vol.All(
            str, vol.Length(min=1, max=32), vol.Match(r"^[0-9]+$")
        ),
    }
)
@websocket_api.async_response
async def ws_ring_history(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    from .websocket import resolve_ring

    resolved = resolve_ring(hass, msg["entry_id"])
    if resolved is None or resolved[0].ring_history is None:
        connection.send_error(msg["id"], "not_found", "Ring bridge is not loaded")
        return
    page = await resolved[0].ring_history.async_page(msg["limit"], msg.get("cursor"))
    connection.send_result(msg["id"], page)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "media_bridge/ring/identity/update",
        vol.Required("entry_id"): str,
        vol.Required("selection"): {
            vol.Required("device_name"): vol.In(("ring", "home_assistant", "custom")),
            vol.Required("location_name"): vol.In(("ring", "home_assistant", "custom")),
            vol.Required("city"): vol.In(("ring", "custom")),
        },
        vol.Required("custom"): {
            vol.Required("device_name"): vol.All(str, vol.Length(max=128)),
            vol.Required("location_name"): vol.All(str, vol.Length(max=128)),
            vol.Required("city"): vol.All(str, vol.Length(max=128)),
        },
    }
)
@websocket_api.async_response
async def ws_ring_identity_update(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Persist a bounded, authenticated Ring display-identity choice."""
    from .websocket import resolve_ring

    resolved = resolve_ring(hass, msg["entry_id"])
    if resolved is None or resolved[0].ring_history is None:
        connection.send_error(msg["id"], "not_found", "Ring bridge is not loaded")
        return
    try:
        result = await resolved[0].ring_history.async_update_identity(
            msg["selection"], msg["custom"]
        )
    except ValueError:
        connection.send_error(msg["id"], "invalid_format", "Ring identity is invalid")
        return
    connection.send_result(msg["id"], result)
