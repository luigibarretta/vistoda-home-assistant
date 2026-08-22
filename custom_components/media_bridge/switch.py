"""Global Vistoda Ring policy switches persisted in config entry options."""

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    CONF_ALIAS,
    CONF_PROVIDER,
    CONF_RING_AUTO_RECORD,
    CONF_RING_DELEGATE_CONTROLS,
    PROVIDER_RING,
    SIGNAL_RING_POLICY_CHANGED,
)
from .ring_facade import official_controls_available, ring_device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Expose global policies only for Ring entries."""
    if entry.data[CONF_PROVIDER] != PROVIDER_RING:
        return
    official_available = official_controls_available(hass)
    if not official_available and entry.options.get(CONF_RING_DELEGATE_CONTROLS, False):
        hass.config_entries.async_update_entry(
            entry,
            options={**entry.options, CONF_RING_DELEGATE_CONTROLS: False},
        )
    async_add_entities(
        [
            RingPolicySwitch(
                hass,
                entry,
                CONF_RING_AUTO_RECORD,
                "ring_auto_record",
                "mdi:record-rec",
                default=False,
            ),
            RingPolicySwitch(
                hass,
                entry,
                CONF_RING_DELEGATE_CONTROLS,
                "ring_delegate_controls",
                "mdi:swap-horizontal",
                default=official_available,
                available=official_available,
            ),
        ]
    )


class RingPolicySwitch(SwitchEntity):
    """One server-side setting shared by every browser and automation."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        option: str,
        translation_key: str,
        icon: str,
        *,
        default: bool,
        available: bool = True,
    ) -> None:
        self._hass = hass
        self._entry = entry
        self._option = option
        self._default = default
        self._attr_translation_key = translation_key
        self._attr_icon = icon
        self._attr_available = available
        alias = entry.data[CONF_ALIAS]
        self._attr_unique_id = f"ring-{alias}-facade-{option.removeprefix('ring_')}"
        self._attr_device_info = ring_device_info(alias)

    @property
    def is_on(self) -> bool:
        """Read the current globally persisted value."""
        return bool(self._entry.options.get(self._option, self._default))

    async def async_turn_on(self, **_kwargs) -> None:
        """Enable this policy, failing closed if delegation is unavailable."""
        if not self.available:
            raise HomeAssistantError("Official Ring controls are not available")
        self._set(True)

    async def async_turn_off(self, **_kwargs) -> None:
        """Disable this policy."""
        self._set(False)

    def _set(self, value: bool) -> None:
        self._hass.config_entries.async_update_entry(
            self._entry,
            options={**self._entry.options, self._option: value},
        )
        self.async_write_ha_state()
        async_dispatcher_send(self._hass, SIGNAL_RING_POLICY_CHANGED, self._entry.entry_id)
