"""Home Assistant service boundary for private Ring recording imports."""

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ServiceValidationError

from . import BridgeRuntime
from .const import CONF_ALIAS, CONF_PROVIDER, DOMAIN, PROVIDER_RING
from .errors import BridgeError

SERVICE_IMPORT_RING_RECORDING = "import_ring_recording"


@callback
def async_register(hass: HomeAssistant) -> None:
    """Register the ding-triggered import service once."""

    async def handle(call: ServiceCall) -> None:
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
        if runtime.client is None:
            raise ServiceValidationError("Vistoda Ring bridge is unavailable")
        try:
            import_id = await runtime.client.import_ring_recording(
                entry.data[CONF_ALIAS], call.data["triggered_at"]
            )
        except BridgeError as error:
            raise ServiceValidationError("Ring recording import was rejected") from error
        hass.bus.async_fire(
            "vistoda_ring_recording_import_started",
            {"entry_id": entry.entry_id, "import_id": import_id},
        )

    hass.services.async_register(
        DOMAIN,
        SERVICE_IMPORT_RING_RECORDING,
        handle,
        schema=vol.Schema({vol.Required("triggered_at"): vol.Coerce(int)}),
    )
