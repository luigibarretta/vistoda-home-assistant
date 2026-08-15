"""Authenticated HA WebSocket boundary for Ring browser audio."""

from contextlib import suppress
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from . import BridgeRuntime
from .const import CONF_ALIAS, CONF_PROVIDER, DOMAIN, PROVIDER_RING
from .errors import BridgeError, EnrollmentBusyError, RateLimitedError


@callback
def async_register(hass: HomeAssistant) -> None:
    """Register the three bounded commands once for the integration."""
    websocket_api.async_register_command(hass, ws_ring_info)
    websocket_api.async_register_command(hass, ws_ring_start)
    websocket_api.async_register_command(hass, ws_ring_stop)
    websocket_api.async_register_command(hass, ws_ring_recordings)


@websocket_api.websocket_command({vol.Required("type"): "media_bridge/ring/info"})
@callback
def ws_ring_info(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return non-secret loaded Ring entries."""
    entries = []
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.data.get(CONF_PROVIDER) != PROVIDER_RING:
            continue
        runtime: BridgeRuntime | None = hass.data.get(DOMAIN, {}).get(entry.entry_id)
        entries.append(
            {
                "entry_id": entry.entry_id,
                "name": entry.title,
                "available": bool(runtime and runtime.coordinator.last_update_success),
            }
        )
    connection.send_result(msg["id"], {"entries": entries})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "media_bridge/ring/session/create",
        vol.Required("entry_id"): str,
        vol.Required("offer_sdp"): vol.All(str, vol.Length(min=1, max=65536)),
        vol.Required("mode"): vol.In(("listen", "talk")),
    }
)
@websocket_api.async_response
async def ws_ring_start(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Negotiate one session without exposing bridge credentials."""
    resolved = resolve_ring(hass, msg["entry_id"])
    if resolved is None:
        connection.send_error(msg["id"], "not_found", "Ring bridge is not loaded")
        return
    runtime, alias = resolved
    try:
        result = await runtime.client.start_ring_audio(alias, msg["offer_sdp"], msg["mode"])
    except EnrollmentBusyError:
        connection.send_error(msg["id"], "session_busy", "Ring audio is already in use")
        return
    except RateLimitedError:
        connection.send_error(msg["id"], "cooldown", "Ring audio is cooling down")
        return
    except BridgeError:
        connection.send_error(msg["id"], "unavailable", "Ring audio is unavailable")
        return
    connection.send_result(
        msg["id"],
        {
            "session_id": result.session_id,
            "answer_sdp": result.answer_sdp,
            "ice_candidates": [
                {
                    "candidate": item.candidate,
                    "sdp_mline_index": item.sdp_mline_index,
                }
                for item in result.ice_candidates
            ],
            "expires_in": result.expires_in,
        },
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "media_bridge/ring/session/delete",
        vol.Required("entry_id"): str,
        vol.Required("session_id"): vol.All(str, vol.Length(min=1, max=64)),
    }
)
@websocket_api.async_response
async def ws_ring_stop(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Close a session; repeated calls remain successful."""
    resolved = resolve_ring(hass, msg["entry_id"])
    if resolved is not None:
        runtime, alias = resolved
        with suppress(BridgeError):
            await runtime.client.stop_ring_audio(alias, msg["session_id"])
    connection.send_result(msg["id"])


def resolve_ring(hass: HomeAssistant, entry_id: str) -> tuple[BridgeRuntime, str] | None:
    """Resolve only a loaded Ring config entry."""
    entry = hass.config_entries.async_get_entry(entry_id)
    runtime = hass.data.get(DOMAIN, {}).get(entry_id)
    if (
        entry is None
        or entry.data.get(CONF_PROVIDER) != PROVIDER_RING
        or not isinstance(runtime, BridgeRuntime)
        or runtime.client is None
    ):
        return None
    return runtime, entry.data[CONF_ALIAS]


@websocket_api.websocket_command(
    {
        vol.Required("type"): "media_bridge/ring/recordings/list",
        vol.Required("entry_id"): str,
    }
)
@websocket_api.async_response
async def ws_ring_recordings(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return bounded archive metadata without bridge credentials or URLs."""
    resolved = resolve_ring(hass, msg["entry_id"])
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
