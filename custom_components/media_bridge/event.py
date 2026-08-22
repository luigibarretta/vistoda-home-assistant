"""Ring Intercom events mirrored from the official integration."""

from homeassistant.components.event import EventDeviceClass, EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_PROVIDER, PROVIDER_RING
from .ring_contract import (
    DING,
    INTERCOM_UNLOCK,
    RingSourceSpec,
    timestamp_is_recent,
    timestamps_match,
)
from .ring_facade import RingFacadeEntity

EVENTS = (
    (DING, "ring_ding", "ring", EventDeviceClass.DOORBELL),
    (INTERCOM_UNLOCK, "ring_intercom_unlock", "intercom_unlock", EventDeviceClass.BUTTON),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add active Ring events without synthesizing historical events."""
    if entry.data[CONF_PROVIDER] == PROVIDER_RING:
        async_add_entities(
            RingEvent(hass, entry, spec, translation_key, event_type, device_class)
            for spec, translation_key, event_type, device_class in EVENTS
        )


class RingEvent(RingFacadeEntity, EventEntity):
    """Forward one future official Ring event exactly once."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        spec: RingSourceSpec,
        translation_key: str,
        event_type: str,
        device_class: EventDeviceClass,
    ) -> None:
        super().__init__(hass, entry, spec)
        self._attr_translation_key = translation_key
        self._attr_event_types = [event_type]
        self._attr_device_class = device_class

    async def async_get_last_state(self):
        """Restore only a facade event that matches the official source event."""
        restored = await super().async_get_last_state()
        source = self.source_state
        if restored is None or source is None:
            return None
        return restored if timestamps_match(restored.state, source.state) else None

    @callback
    def handle_source_event(self, event: Event) -> None:
        """Forward only real source transitions, never replay startup history."""
        old_state = event.data.get("old_state")
        state = event.data.get("new_state")
        if state is None:
            return
        event_type = state.attributes.get("event_type")
        if (
            old_state is None
            or old_state.state == state.state
            or not timestamp_is_recent(state.state)
            or event_type not in self._attr_event_types
        ):
            self.async_write_ha_state()
            return
        attributes = {
            key: value
            for key, value in state.attributes.items()
            if key not in {"event_type", "event_types", "friendly_name", "attribution"}
        }
        self._trigger_event(event_type, attributes)
        self.async_write_ha_state()
