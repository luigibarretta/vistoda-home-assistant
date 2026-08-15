"""Private Ring recording inventory sensor."""

from datetime import UTC, datetime

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import BridgeRuntime
from .const import CONF_ALIAS, CONF_PROVIDER, DOMAIN, PROVIDER_RING
from .errors import BridgeError


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add an archive sensor only for Ring."""
    if entry.data[CONF_PROVIDER] == PROVIDER_RING:
        async_add_entities([RingRecordingArchive(hass.data[DOMAIN][entry.entry_id], entry)])


class RingRecordingArchive(SensorEntity):
    """Expose count and newest private recording without media URLs."""

    _attr_has_entity_name = True
    _attr_name = "Registrazioni chiamate"
    _attr_icon = "mdi:record-rec"
    _attr_native_unit_of_measurement = "registrazioni"
    _attr_should_poll = True

    def __init__(self, runtime: BridgeRuntime, entry: ConfigEntry) -> None:
        self._runtime = runtime
        self._alias = entry.data[CONF_ALIAS]
        self._attr_unique_id = f"ring-{self._alias}-recordings"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"ring:{self._alias}")},
            "name": "Vistoda · RING",
            "manufacturer": "Vistoda",
            "model": "Private Rust bridge",
        }
        self._attr_native_value = 0
        self._attr_extra_state_attributes = {
            "retention_days": 30,
            "archive_limit_mib": 512,
        }

    async def async_update(self) -> None:
        """Refresh only bounded metadata from the private bridge."""
        client = self._runtime.client
        if client is None:
            self._attr_available = False
            return
        try:
            recordings = await client.ring_recordings(self._alias)
        except BridgeError:
            self._attr_available = False
            return
        self._attr_available = True
        self._attr_native_value = len(recordings)
        latest = recordings[0] if recordings else None
        self._attr_extra_state_attributes = {
            "retention_days": 30,
            "archive_limit_mib": 512,
            "latest_recording": (
                datetime.fromtimestamp(latest.event_at, UTC).isoformat() if latest else None
            ),
            "latest_size_bytes": latest.bytes if latest else None,
        }
