"""Per-entry EZVIZ control source: the standalone Vistoda app or the official integration.

Standalone (the default) reads and writes settings, arming, detection, PTZ,
connectivity and the account alarm panel through the Vistoda EZVIZ app's own
EZVIZ login. A delegated entry uses Home Assistant's official EZVIZ integration
instead, like the Ring delegation switch. Delegation can only be turned on while
the native cloud coordinator for the bound camera is healthy, and it is forced
back off at setup when that integration cannot serve the camera.
"""

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory

from .const import CONF_EZVIZ_DELEGATE_CONTROLS, CONF_PROVIDER, CONF_URL, DOMAIN, PROVIDER_EZVIZ
from .ezviz_core import delegated, native_controls_available, refresh_core_issue
from .ezviz_identity import delegate_unique_id, device_info

_LOGGER = logging.getLogger(__name__)


def _set_option(hass, entry, value: bool) -> None:
    hass.config_entries.async_update_entry(
        entry, options={**entry.options, CONF_EZVIZ_DELEGATE_CONTROLS: value}
    )


@callback
def async_reload_app_entries(hass, entry, *, include_self: bool) -> None:
    """Reload the loaded entries sharing this app: the account alarm owner may move."""
    from homeassistant.config_entries import ConfigEntryState

    url = entry.data.get(CONF_URL)
    for candidate in hass.config_entries.async_entries(DOMAIN):
        if (
            candidate.data.get(CONF_PROVIDER) == PROVIDER_EZVIZ
            and candidate.data.get(CONF_URL) == url
            and candidate.state is ConfigEntryState.LOADED
            and (include_self or candidate.entry_id != entry.entry_id)
        ):
            hass.config_entries.async_schedule_reload(candidate.entry_id)


@callback
def _enforce(hass, entry, *, include_self: bool) -> None:
    if not delegated(entry) or native_controls_available(hass, entry):
        return
    _LOGGER.warning(
        "Official EZVIZ integration is unavailable for %s: using the Vistoda EZVIZ app",
        entry.title,
    )
    _set_option(hass, entry, False)
    refresh_core_issue(hass)
    async_reload_app_entries(hass, entry, include_self=include_self)


@callback
def enforce_delegate_policy(hass, entry) -> None:
    """Force delegation off at setup when the official integration cannot serve the camera."""
    if not delegated(entry):
        return
    if getattr(hass, "is_running", True):
        # This entry is still setting up and reads the corrected option itself.
        _enforce(hass, entry, include_self=False)
        return
    # Native EZVIZ entries may still be loading: decide once Home Assistant started.
    from homeassistant.helpers.start import async_at_started

    @callback
    def _started(_hass) -> None:
        # The entry already set up in delegated mode, so it reloads as well.
        _enforce(hass, entry, include_self=True)

    entry.async_on_unload(async_at_started(hass, _started))


async def _require_admin(hass, context) -> None:
    """Changing the control source is an administrator setting, like settings/set."""
    from homeassistant.exceptions import ServiceValidationError

    if context is None:
        raise ServiceValidationError("EZVIZ control source requires a Home Assistant context")
    if context.user_id is None:
        return  # Home Assistant-owned automations.
    user = await hass.auth.async_get_user(context.user_id)
    if user is None or not user.is_active or not user.is_admin:
        raise ServiceValidationError("Administrator access required")


class EzvizDelegateSwitch(SwitchEntity):
    """Delegate this camera's controls to the official EZVIZ integration (default off)."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "ezviz_delegate_controls"
    _attr_icon = "mdi:swap-horizontal"
    # Polls in-memory state only, so availability follows the native coordinator.
    _attr_should_poll = True

    def __init__(self, hass, entry) -> None:
        self._hass = hass
        self._entry = entry
        self._attr_unique_id = delegate_unique_id(entry)
        self._attr_device_info = device_info(entry)

    @property
    def is_on(self) -> bool:
        return delegated(self._entry)

    @property
    def available(self) -> bool:
        # Stays available while on, so delegation can always be turned off.
        return self.is_on or native_controls_available(self._hass, self._entry)

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        if self.is_on:
            return {"control_source": "official_ezviz", "source_integration": "ezviz"}
        return {"control_source": "vistoda", "source_integration": DOMAIN}

    async def async_turn_on(self, **_kwargs) -> None:
        await _require_admin(self._hass, self._context)
        if not native_controls_available(self._hass, self._entry):
            raise HomeAssistantError("Official EZVIZ controls are not available for this camera")
        self._set(True)

    async def async_turn_off(self, **_kwargs) -> None:
        await _require_admin(self._hass, self._context)
        self._set(False)

    def _set(self, value: bool) -> None:
        if self.is_on == value:
            return
        _set_option(self._hass, self._entry, value)
        self.async_write_ha_state()
        refresh_core_issue(self._hass)
        # Routing follows the option at once; the reload adds or removes the
        # Vistoda account alarm panel, which exists only in standalone mode.
        async_reload_app_entries(self._hass, self._entry, include_self=True)
