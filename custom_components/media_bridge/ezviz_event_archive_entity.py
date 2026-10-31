"""Diagnostic problem sensor for the EZVIZ event archive (on during a storage outage)."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import EntityCategory

from .const import ezviz_event_archive_signal
from .ezviz_identity import device_info, entity_prefix


class EzvizEventArchiveProblem(BinarySensorEntity):
    """Available while the entry archives events; on while the storage is unreachable."""

    _attr_has_entity_name = True
    _attr_translation_key = "ezviz_event_archive_problem"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_should_poll = False

    def __init__(self, entry) -> None:
        self._entry = entry
        self._attr_unique_id = f"{entity_prefix(entry)}event-archive-problem"
        self._attr_device_info = device_info(entry)

    @property
    def _archiver(self):
        return getattr(getattr(self._entry, "runtime_data", None), "ezviz_events", None)

    @property
    def available(self) -> bool:
        return bool(self._archiver and self._archiver.enabled)

    @property
    def is_on(self) -> bool:
        return bool(self._archiver and self._archiver.unavailable)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        signal = ezviz_event_archive_signal(self._entry.entry_id)
        self.async_on_remove(async_dispatcher_connect(self.hass, signal, self.async_write_ha_state))
