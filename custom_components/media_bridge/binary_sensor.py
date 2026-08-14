"""Bridge availability entity."""

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import BridgeRuntime
from .const import CONF_ALIAS, CONF_PROVIDER, DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add one connectivity entity."""
    runtime: BridgeRuntime = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([BridgeConnectivity(runtime, entry)])


class BridgeConnectivity(CoordinatorEntity, BinarySensorEntity):
    """Report whether the private bridge answers its health contract."""

    _attr_has_entity_name = True
    _attr_name = "Connessione"

    def __init__(self, runtime: BridgeRuntime, entry: ConfigEntry) -> None:
        super().__init__(runtime.coordinator)
        provider = entry.data[CONF_PROVIDER]
        alias = entry.data[CONF_ALIAS]
        self._attr_unique_id = f"{provider}-{alias}-bridge-connectivity"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{provider}:{alias}")},
            "name": f"Vistoda · {provider.upper()}",
            "manufacturer": "Vistoda",
            "model": "Private Rust bridge",
        }

    @property
    def is_on(self) -> bool:
        """Return current coordinator success."""
        return self.coordinator.last_update_success

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Expose only non-secret version metadata."""
        return {"version": self.coordinator.data or "unknown"}
