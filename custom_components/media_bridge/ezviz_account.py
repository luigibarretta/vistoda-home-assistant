"""Account-wide EZVIZ defence mode, owned by one camera entry per Vistoda EZVIZ app.

One Vistoda EZVIZ app holds exactly one EZVIZ login, and several camera entries
can point at the same app (same URL). The account alarm panel therefore belongs
to a single owner: the enabled standalone EZVIZ entry with the smallest entry_id
among the entries sharing that app URL. Entries delegated to the official EZVIZ
integration rely on its own alarm panel, so they never own a duplicate one. The
unique_id carries the owner's entry_id, so it stays stable when the app URL
changes and never duplicates across entries.
"""

import logging
from dataclasses import dataclass
from datetime import timedelta

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client_ezviz_controls import (
    EzvizControlConflictError,
    EzvizControlUnconfirmedError,
)
from .client_ezviz_media import EzvizFeatureUnsupportedError
from .const import CONF_PROVIDER, CONF_URL, DOMAIN, PROVIDER_EZVIZ
from .errors import BridgeError, ReauthRequiredError

_LOGGER = logging.getLogger(__name__)
DEFENCE_INTERVAL = timedelta(seconds=60)
# Same mapping as Home Assistant core's EZVIZ alarm panel.
MODE_STATES = {"home": "disarmed", "away": "armed_away", "sleep": "armed_home"}
STATE_MODES = {state: mode for mode, state in MODE_STATES.items()}


def account_owner_id(hass, entry) -> str | None:
    """Pick the one enabled standalone EZVIZ entry that owns the app's account entities."""
    from .ezviz_core import delegated

    url = entry.data.get(CONF_URL)
    owners = sorted(
        candidate.entry_id
        for candidate in hass.config_entries.async_entries(DOMAIN)
        if candidate.data.get(CONF_PROVIDER) == PROVIDER_EZVIZ
        and candidate.data.get(CONF_URL) == url
        and getattr(candidate, "disabled_by", None) is None
        and not delegated(candidate)
    )
    return owners[0] if owners else None


def defence_unique_id(owner_entry_id: str) -> str:
    return f"ezviz-{owner_entry_id}-account-defence"


def account_device_info(owner_entry_id: str) -> dict:
    return {
        "identifiers": {(DOMAIN, f"ezviz-account:{owner_entry_id}")},
        "name": "Vistoda · EZVIZ · Account",
        "manufacturer": "EZVIZ",
        "model": "Vistoda EZVIZ account",
    }


@dataclass(frozen=True, slots=True)
class EzvizDefenceStatus:
    supported: bool
    mode: str | None = None


def reports_defence(data) -> bool:
    return isinstance(data, EzvizDefenceStatus) and data.supported


class DefenceRejectedError(Exception):
    """The app refused or could not confirm the new mode; carries a stable code."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class EzvizDefenceCoordinator(DataUpdateCoordinator):
    """Poll the account defence mode while the owner's bridge is healthy."""

    def __init__(self, hass, entry, client, bridge) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
            name="Vistoda EZVIZ account defence",
            update_interval=DEFENCE_INTERVAL,
            config_entry=entry,
        )
        self.client = client
        self.bridge = bridge

    async def _async_update_data(self) -> EzvizDefenceStatus:
        if not getattr(self.bridge, "last_update_success", False):
            raise UpdateFailed("EZVIZ bridge is unavailable")
        try:
            return EzvizDefenceStatus(True, await self.client.ezviz_account_defence())
        except EzvizFeatureUnsupportedError:
            return EzvizDefenceStatus(False)
        except ReauthRequiredError as error:
            raise ConfigEntryAuthFailed("EZVIZ session requires a new login") from error
        except BridgeError as error:
            raise UpdateFailed("EZVIZ account defence check failed") from error

    async def async_set_mode(self, mode: str) -> None:
        """Compare-and-set through the app; never report an unconfirmed mode."""
        current = self.data.mode if reports_defence(self.data) else None
        try:
            confirmed = await self.client.ezviz_set_account_defence(mode, current)
        except EzvizControlConflictError as error:
            await self.async_refresh()
            raise DefenceRejectedError("conflict") from error
        except EzvizControlUnconfirmedError as error:
            await self.async_refresh()
            raise DefenceRejectedError("unconfirmed") from error
        except BridgeError as error:
            # A failed call may still have reached EZVIZ: show the real state.
            await self.async_refresh()
            raise DefenceRejectedError("unavailable") from error
        if confirmed == mode:
            self.async_set_updated_data(EzvizDefenceStatus(True, confirmed))
            return
        await self.async_refresh()
        if not reports_defence(self.data) or self.data.mode != mode:
            raise DefenceRejectedError("unconfirmed")
