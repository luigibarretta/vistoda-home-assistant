"""Ring Intercom actions delegated to the official integration."""

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_PROVIDER, DOMAIN, PROVIDER_RING
from .ring_contract import OPEN_DOOR
from .ring_facade import RingFacadeEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the safe Ring door action only to the Ring entry."""
    if entry.data[CONF_PROVIDER] == PROVIDER_RING:
        async_add_entities([RingOpenDoor(hass, entry)])


class RingOpenDoor(RingFacadeEntity, ButtonEntity):
    """Ask the official Ring integration to open the entrance door."""

    _attr_translation_key = "ring_open_door"
    _attr_icon = "mdi:door-open"
    _attr_native_capable = True

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(hass, entry, OPEN_DOOR)

    async def async_press(self) -> None:
        """Open through the selected path; never retry an unlock."""
        if self.delegated:
            await self.call_source_service("button", "press", {})
            return
        client = self._hass.data[DOMAIN][self._entry.entry_id].client
        if client is None:
            raise RuntimeError("Native Ring bridge is unavailable")
        await client.unlock_ring(self._alias)
