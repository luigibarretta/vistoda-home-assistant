"""Availability coordinator for one bridge entry."""

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import BridgeClient
from .const import CONF_PROVIDER, PROVIDER_EZVIZ
from .errors import BindingMismatchError, BridgeError, ReauthRequiredError
from .repairs import update_bridge_issue, update_ezviz_binding_issue

_LOGGER = logging.getLogger(__name__)


class BridgeCoordinator(DataUpdateCoordinator[str]):
    """Poll only minimal health; media remains on demand."""

    def __init__(self, hass, client: BridgeClient, entry: ConfigEntry, name: str) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
            name=name,
            update_interval=timedelta(seconds=60),
            config_entry=entry,
        )
        self.client = client
        self.entry = entry

    async def _async_update_data(self) -> str:
        ezviz = self.entry.data.get(CONF_PROVIDER) == PROVIDER_EZVIZ
        if ezviz:
            from .ezviz_core import refresh_core_issue

            refresh_core_issue(self.hass)
        try:
            version = (await self.client.health()).version
        except BridgeError as error:
            # The repair waits out restarts and blips; entities still go unavailable now.
            update_bridge_issue(self.hass, self.entry, available=False)
            raise UpdateFailed("bridge health check failed") from error
        update_bridge_issue(self.hass, self.entry, available=True)
        if ezviz:
            await async_check_ezviz_binding(self.hass, self.entry, self.client)
        return version


async def async_check_ezviz_binding(hass, entry, client, *, bind: bool = False) -> None:
    """Verify (or pin, with `bind`) the physical camera; fail closed either way.

    A changed camera is reported at once. An identity endpoint that merely does
    not answer is an outage: the repair waits for the grace and never claims the
    camera changed. A revoked EZVIZ session starts the reauthentication flow.
    """
    from .ezviz_binding import CONF_EZVIZ_SOURCE_ID, async_bind_native, async_verify_native

    try:
        if bind:
            await async_bind_native(hass, entry, client)
        elif CONF_EZVIZ_SOURCE_ID in entry.data:
            await async_verify_native(entry, client)
    except ReauthRequiredError as error:
        raise ConfigEntryAuthFailed("EZVIZ session requires a new login") from error
    except BindingMismatchError as error:
        update_ezviz_binding_issue(hass, entry, available=False, mismatch=True)
        raise UpdateFailed("EZVIZ physical camera identity changed") from error
    except BridgeError as error:
        update_ezviz_binding_issue(hass, entry, available=False)
        raise UpdateFailed("EZVIZ camera identity could not be verified") from error
    update_ezviz_binding_issue(hass, entry, available=True)
