"""Diagnostic microSD entities for one EZVIZ camera (Vistoda EZVIZ 0.9+)."""

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .client_ezviz_media import STORAGE_STATUSES
from .ezviz_identity import device_info, entity_prefix
from .ezviz_media import (
    MICROSD_PROBLEM_SUFFIX,
    MICROSD_SUFFIX,
    PROBLEM_STATUSES,
    storage_of,
)


class _EzvizMediaEntity(CoordinatorEntity):
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, entry, suffix: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entity_prefix(entry)}{suffix}"
        self._attr_device_info = device_info(entry)

    @property
    def _storage(self):
        return storage_of(self.coordinator.data)

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self._storage is not None


class EzvizMicroSdSensor(_EzvizMediaEntity, SensorEntity):
    """State is the card status; capacity stays an attribute."""

    _attr_translation_key = "ezviz_microsd"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_icon = "mdi:micro-sd"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, MICROSD_SUFFIX)
        self._attr_options = list(STORAGE_STATUSES)

    @property
    def native_value(self) -> str | None:
        storage = self._storage
        return storage.status if storage else None

    @property
    def extra_state_attributes(self) -> dict:
        storage = self._storage
        return {"capacity_mb": storage.capacity_mb if storage else None}


class EzvizMicroSdProblem(_EzvizMediaEntity, BinarySensorEntity):
    """On for a missing, unformatted or failed card; unknown stays unknown."""

    _attr_translation_key = "ezviz_microsd_problem"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, MICROSD_PROBLEM_SUFFIX)

    @property
    def is_on(self) -> bool | None:
        storage = self._storage
        if storage is None or storage.status == "unknown":
            return None
        return storage.status in PROBLEM_STATUSES
