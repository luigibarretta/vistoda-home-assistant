"""Authenticated HA WebSocket boundary for Ring browser audio."""

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er

from . import BridgeRuntime
from .const import CONF_ALIAS, CONF_PROVIDER, DOMAIN, PROVIDER_RING
from .errors import BridgeError, EnrollmentBusyError, RateLimitedError
from .ring_recording_websocket import async_register as async_register_recordings
from .ring_session_log import async_ended, async_started

CONTROL_KEYS = (
    "open_door",
    "battery",
    "doorbell_volume",
    "mic_volume",
    "voice_volume",
    "auto_record",
    "delegate_controls",
)
STOP_REASONS = ("user_stop", "panel_closed", "client_expired", "connection_ended", "start_failed")


@callback
def async_register(hass: HomeAssistant) -> None:
    """Register the three bounded commands once for the integration."""
    websocket_api.async_register_command(hass, ws_ring_info)
    websocket_api.async_register_command(hass, ws_ring_start)
    websocket_api.async_register_command(hass, ws_ring_stop)
    async_register_recordings(hass)


@websocket_api.websocket_command({vol.Required("type"): "media_bridge/ring/info"})
@callback
def ws_ring_info(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return non-secret loaded Ring entries."""
    entries = []
    registry = er.async_get(hass)
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.data.get(CONF_PROVIDER) != PROVIDER_RING:
            continue
        runtime: BridgeRuntime | None = hass.data.get(DOMAIN, {}).get(entry.entry_id)
        controls = {}
        prefix = f"ring-{entry.data[CONF_ALIAS]}-facade-"
        for entity in registry.entities.values():
            if entity.config_entry_id != entry.entry_id or not entity.unique_id.startswith(prefix):
                continue
            key = entity.unique_id.removeprefix(prefix)
            if key in CONTROL_KEYS:
                controls[key] = entity.entity_id
        entries.append(
            {
                "entry_id": entry.entry_id,
                "name": entry.title,
                "available": bool(runtime and runtime.coordinator.last_update_success),
                "controls": controls,
            }
        )
    connection.send_result(msg["id"], {"entries": entries})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "media_bridge/ring/session/create",
        vol.Required("entry_id"): str,
        vol.Required("offer_sdp"): vol.All(str, vol.Length(min=1, max=65536)),
        vol.Required("mode"): vol.In(("listen", "talk")),
        vol.Required("ice_gathering_ms"): vol.All(vol.Coerce(int), vol.Range(min=0, max=60000)),
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
        result = await runtime.client.start_ring_audio(
            alias, msg["offer_sdp"], msg["mode"], msg["ice_gathering_ms"]
        )
    except EnrollmentBusyError:
        connection.send_error(msg["id"], "session_busy", "Ring audio is already in use")
        return
    except RateLimitedError:
        connection.send_error(msg["id"], "cooldown", "Ring audio is cooling down")
        return
    except BridgeError:
        connection.send_error(msg["id"], "unavailable", "Ring audio is unavailable")
        return
    async_started(hass, alias, result.session_id, msg["mode"], msg["ice_gathering_ms"])
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
        vol.Required("reason"): vol.In(STOP_REASONS),
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
    acknowledged = False
    if resolved is not None:
        runtime, alias = resolved
        try:
            await runtime.client.stop_ring_audio(alias, msg["session_id"], msg["reason"])
            acknowledged = True
        except BridgeError:
            pass
    async_ended(hass, msg["session_id"], msg["reason"], acknowledged)
    connection.send_result(msg["id"], {"bridge_acknowledged": acknowledged})


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
