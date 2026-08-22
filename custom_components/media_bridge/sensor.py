"""Private recordings and Ring Intercom sensor facade."""

from datetime import UTC, datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import BridgeRuntime
from .const import CONF_ALIAS, CONF_PROVIDER, DOMAIN, PROVIDER_RING
from .errors import BridgeError
from .ring_contract import BATTERY, LAST_ACTIVITY, RingSourceSpec
from .ring_facade import RingFacadeEntity

RING_SENSORS = (
    (BATTERY, "ring_battery", SensorDeviceClass.BATTERY),
    (LAST_ACTIVITY, "ring_last_activity", SensorDeviceClass.TIMESTAMP),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add private archive and provider-owned Ring sensors."""
    if entry.data[CONF_PROVIDER] == PROVIDER_RING:
        async_add_entities(
            [RingRecordingArchive(hass.data[DOMAIN][entry.entry_id], entry)]
            + [
                RingOfficialSensor(hass, entry, spec, translation_key, device_class)
                for spec, translation_key, device_class in RING_SENSORS
            ]
        )


class RingOfficialSensor(RingFacadeEntity, SensorEntity):
    """Mirror one active diagnostic from the official Ring integration."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        spec: RingSourceSpec,
        translation_key: str,
        device_class: SensorDeviceClass,
    ) -> None:
        super().__init__(hass, entry, spec)
        self._status_key = spec.key
        self._attr_translation_key = translation_key
        self._attr_device_class = device_class
        if device_class == SensorDeviceClass.BATTERY:
            self._attr_native_unit_of_measurement = "%"
            self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        """Return a typed copy from the selected provider path."""
        if not self.delegated:
            status = self.native_status
            value = getattr(status, self._status_key) if status else None
            if self.device_class == SensorDeviceClass.TIMESTAMP and value is not None:
                return datetime.fromtimestamp(value, UTC)
            return value
        state = self.source_state
        if state is None:
            return None
        if self.device_class == SensorDeviceClass.BATTERY:
            try:
                return int(state.state)
            except ValueError:
                return None
        return dt_util.parse_datetime(state.state)

    @property
    def extra_state_attributes(self) -> dict:
        """Preserve useful activity metadata and delegation evidence."""
        attributes = super().extra_state_attributes
        if (
            self.delegated
            and self.device_class == SensorDeviceClass.TIMESTAMP
            and self.source_state
        ):
            attributes.update(
                {
                    key: value
                    for key, value in self.source_state.attributes.items()
                    if key
                    not in {
                        "friendly_name",
                        "attribution",
                        "device_class",
                    }
                }
            )
        return attributes


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
                datetime.fromtimestamp(latest.ended_at, UTC).isoformat() if latest else None
            ),
            "latest_size_bytes": latest.bytes if latest else None,
        }

    _attr_native_capable = True
