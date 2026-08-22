"""Ring Intercom volume controls delegated to the official integration."""

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_PROVIDER, DOMAIN, PROVIDER_RING
from .ring_contract import DOORBELL_VOLUME, MIC_VOLUME, VOICE_VOLUME, RingSourceSpec
from .ring_facade import RingFacadeEntity

VOLUMES = (
    (DOORBELL_VOLUME, "ring_doorbell_volume", 8.0),
    (MIC_VOLUME, "ring_mic_volume", 11.0),
    (VOICE_VOLUME, "ring_voice_volume", 11.0),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add all active official Ring Intercom levels."""
    if entry.data[CONF_PROVIDER] == PROVIDER_RING:
        async_add_entities(
            RingVolume(hass, entry, spec, translation_key, maximum)
            for spec, translation_key, maximum in VOLUMES
        )


class RingVolume(RingFacadeEntity, NumberEntity):
    """Mirror and set one provider-owned integer volume."""

    _attr_native_min_value = 0.0
    _attr_native_step = 1.0
    _attr_mode = NumberMode.SLIDER
    _attr_icon = "mdi:volume-high"
    _attr_native_capable = True

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        spec: RingSourceSpec,
        translation_key: str,
        maximum: float,
    ) -> None:
        super().__init__(hass, entry, spec)
        self._setting = spec.key
        self._attr_translation_key = translation_key
        self._attr_native_max_value = maximum

    @property
    def native_value(self) -> float | None:
        """Return the selected official or native Ring value."""
        if not self.delegated:
            status = self.native_status
            value = getattr(status, self._setting) if status else None
            return float(value) if value is not None else None
        try:
            return float(self.source_state.state) if self.source_state else None
        except ValueError:
            return None

    async def async_set_native_value(self, value: float) -> None:
        """Validate through NumberEntity and write through the selected path."""
        if self.delegated:
            await self.call_source_service("number", "set_value", {"value": value})
            return
        client = self._hass.data[DOMAIN][self._entry.entry_id].client
        if client is None:
            raise RuntimeError("Native Ring bridge is unavailable")
        await client.set_ring_volume(self._alias, self._setting, int(value))
        await self.refresh_native_status()
