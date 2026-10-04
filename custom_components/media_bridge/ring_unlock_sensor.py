"""Read-only Ring unlock type sensor fed by the shared native status poll."""

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .ring_binding import verified_device_id
from .ring_facade import ring_device_info
from .ring_unlock import unlock_mode_unique_id


def reports_unlock_settings(status) -> bool:
    """Vistoda Ring 0.16+ reports unlock settings; older engines omit them."""
    return getattr(status, "unlock_settings", None) is not None


class RingUnlockModeSensor(CoordinatorEntity, SensorEntity):
    """Expose the intercom unlock type (direct or Ring-to-Open) and its duration."""

    _attr_has_entity_name = True
    _attr_translation_key = "ring_unlock_mode"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:lock-smart"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = unlock_mode_unique_id(entry)
        self._attr_device_info = ring_device_info(entry)

    @property
    def _settings(self):
        return getattr(self.coordinator.data, "unlock_settings", None)

    @property
    def available(self) -> bool:
        """Stay unavailable when the enrolled physical intercom cannot be verified."""
        return (
            self.coordinator.last_update_success
            and verified_device_id(self._entry, self.coordinator.data) is not None
        )

    @property
    def native_value(self) -> str | None:
        settings = self._settings
        return settings.effective_mode if settings else None

    @property
    def extra_state_attributes(self) -> dict:
        settings = self._settings
        return {
            "ring_to_open_enabled": settings.ring_to_open_enabled if settings else None,
            "duration_seconds": settings.duration_seconds if settings else None,
        }
