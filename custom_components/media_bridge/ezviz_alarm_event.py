"""EZVIZ alarm event entity fed by the Vistoda EZVIZ app alarm cursor."""

from homeassistant.components.event import EventEntity
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .client_ezviz_alarms import CATEGORIES
from .const import ezviz_alarm_signal
from .ezviz_identity import device_info, entity_prefix

ATTRIBUTES = ("alarm_id", "alarm_type", "title", "occurred_at", "picture")


class EzvizAlarmEvent(EventEntity):
    """One event per new camera alarm; unavailable while the app lacks the feed."""

    _attr_has_entity_name = True
    _attr_translation_key = "ezviz_alarm"
    _attr_icon = "mdi:alarm-light-outline"
    _attr_should_poll = False

    def __init__(self, runtime, entry) -> None:
        self._runtime = runtime
        self._entry = entry
        self._attr_event_types = list(CATEGORIES)
        self._attr_unique_id = f"{entity_prefix(entry)}alarm"
        self._attr_device_info = device_info(entry)

    @property
    def available(self) -> bool:
        listener = getattr(self._runtime, "ezviz_alarms", None)
        return listener is not None and listener.supported is not False

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, ezviz_alarm_signal(self._entry.entry_id), self.handle_alarm
            )
        )

    async def async_get_last_state(self):
        """Never replay a restored alarm after startup."""
        return None

    @callback
    def handle_alarm(self, data: dict | None) -> None:
        """None only refreshes availability; a dict is one new alarm."""
        if data is not None:
            self._trigger_event(data["category"], {key: data[key] for key in ATTRIBUTES})
        self.async_write_ha_state()
