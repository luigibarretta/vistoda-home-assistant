"""One EZVIZ account alarm panel per Vistoda EZVIZ app (Vistoda EZVIZ 0.10+)."""

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_PROVIDER, DOMAIN, PROVIDER_EZVIZ
from .entity_gate import async_add_when_supported
from .ezviz_account import (
    MODE_STATES,
    DefenceRejectedError,
    EzvizDefenceCoordinator,
    account_device_info,
    account_owner_id,
    defence_unique_id,
    reports_defence,
)

MESSAGES = {
    "conflict": "The EZVIZ defence mode changed meanwhile; check it and try again",
    "unconfirmed": "EZVIZ did not confirm the new defence mode",
    "unavailable": "The Vistoda EZVIZ app could not change the defence mode",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Only the owner entry of an app creates the panel, and only once supported."""
    if entry.data.get(CONF_PROVIDER) != PROVIDER_EZVIZ:
        return
    runtime = hass.data[DOMAIN][entry.entry_id]
    if getattr(runtime, "client", None) is None or account_owner_id(hass, entry) != entry.entry_id:
        return
    defence = EzvizDefenceCoordinator(hass, entry, runtime.client, runtime.coordinator)
    runtime.ezviz_defence = defence
    async_add_when_supported(
        entry,
        defence,
        reports_defence,
        lambda: [EzvizAccountAlarm(defence, entry.entry_id)],
        async_add_entities,
    )
    # Off the setup path: an older app answers 404 and adds nothing.
    entry.async_create_background_task(
        hass, defence.async_refresh(), f"Vistoda EZVIZ defence {entry.entry_id}"
    )


class EzvizAccountAlarm(CoordinatorEntity, AlarmControlPanelEntity):
    """Disarm = home, arm home = sleep, arm away = away, like HA core's EZVIZ panel."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_code_arm_required = False
    _attr_supported_features = (
        AlarmControlPanelEntityFeature.ARM_HOME | AlarmControlPanelEntityFeature.ARM_AWAY
    )

    def __init__(self, coordinator: EzvizDefenceCoordinator, owner_entry_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = defence_unique_id(owner_entry_id)
        self._attr_device_info = account_device_info(owner_entry_id)
        self._attr_extra_state_attributes = {"scope": "account", "source": "vistoda_ezviz"}

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and reports_defence(self.coordinator.data)

    @property
    def alarm_state(self) -> AlarmControlPanelState | None:
        data = self.coordinator.data
        state = MODE_STATES.get(data.mode) if reports_defence(data) else None
        return AlarmControlPanelState(state) if state else None

    async def _async_set(self, mode: str) -> None:
        try:
            await self.coordinator.async_set_mode(mode)
        except DefenceRejectedError as error:
            raise HomeAssistantError(MESSAGES[error.code]) from error

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        await self._async_set("home")

    async def async_alarm_arm_home(self, code: str | None = None) -> None:
        await self._async_set("sleep")

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        await self._async_set("away")
