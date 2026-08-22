"""Home Assistant service boundary for safe Ring door opening."""

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ServiceValidationError

from . import BridgeRuntime
from .const import CONF_ALIAS, CONF_PROVIDER, DOMAIN, PROVIDER_RING
from .errors import BridgeError
from .ring_contract import OPEN_DOOR
from .ring_facade import resolve_source

SERVICE_OPEN_RING_DOOR = "open_ring_door"


@callback
def async_register(hass: HomeAssistant) -> None:
    """Register one Vistoda-first unlock action with a safe fallback."""

    async def handle(_call: ServiceCall) -> None:
        candidates = []
        for entry in hass.config_entries.async_entries(DOMAIN):
            runtime = hass.data.get(DOMAIN, {}).get(entry.entry_id)
            if entry.data.get(CONF_PROVIDER) == PROVIDER_RING and isinstance(
                runtime, BridgeRuntime
            ):
                candidates.append((entry, runtime))
        if len(candidates) != 1:
            raise ServiceValidationError("Exactly one loaded Vistoda Ring bridge is required")
        entry, runtime = candidates[0]
        alias = entry.data[CONF_ALIAS]
        if runtime.client is not None:
            try:
                status = await runtime.client.ring_status(alias)
            except BridgeError:
                status = None
            if status is not None and status.online:
                try:
                    await runtime.client.unlock_ring(alias)
                except BridgeError as error:
                    raise ServiceValidationError(
                        "Vistoda sent the native command but its outcome is unknown; "
                        "official fallback was suppressed to avoid a duplicate unlock"
                    ) from error
                hass.bus.async_fire("vistoda_ring_door_open_requested", {"path": "native"})
                return
        source = resolve_source(hass, OPEN_DOOR)
        state = hass.states.get(source) if source else None
        if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            raise ServiceValidationError("Neither Vistoda nor official Ring is available")
        await hass.services.async_call("button", "press", {"entity_id": source}, blocking=True)
        hass.bus.async_fire("vistoda_ring_door_open_requested", {"path": "official_fallback"})

    hass.services.async_register(
        DOMAIN,
        SERVICE_OPEN_RING_DOOR,
        handle,
    )
