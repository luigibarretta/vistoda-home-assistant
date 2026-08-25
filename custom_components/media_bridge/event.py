"""Native Ring Intercom events with a bounded official fallback."""

import time

from homeassistant.components.event import EventDeviceClass, EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .client_ring_events import RingPushEvent
from .const import CONF_PROVIDER, DOMAIN, PROVIDER_RING, ring_event_signal
from .ring_contract import (
    DING,
    INTERCOM_UNLOCK,
    RingSourceSpec,
    timestamp_is_recent,
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
    """Prefer native push and suppress a matching official duplicate."""

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
        self._native_event_type = "ding" if spec == DING else "intercom_unlock"
        self._last_native = 0.0

    @property
    def available(self) -> bool:
        """Remain useful with either the native or official event path."""
        runtime = self._hass.data[DOMAIN][self._entry.entry_id]
        native = runtime.ring_events is not None and runtime.coordinator.last_update_success
        return native or super().available

    async def async_added_to_hass(self) -> None:
        """Subscribe to native push after the official fallback is installed."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, ring_event_signal(self._entry.entry_id), self._handle_native
            )
        )

    async def async_get_last_state(self):
        """Never replay a restored call or unlock after startup."""
        return None

    @callback
    def _handle_native(self, event: RingPushEvent) -> None:
        if event.event_type != self._native_event_type:
            return
        self._last_native = time.monotonic()
        self._trigger_event(
            self._attr_event_types[0],
            {
                "source": "vistoda_native",
                "occurred_at": event.occurred_at,
                "sequence": event.sequence,
            },
        )
        self.async_write_ha_state()

    @callback
    def handle_source_event(self, event: Event) -> None:
        """Forward only real source transitions, never replay startup history."""
        if time.monotonic() - self._last_native <= 10:
            self.async_write_ha_state()
            return
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
