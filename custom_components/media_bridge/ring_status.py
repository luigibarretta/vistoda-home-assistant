"""Native Ring status coordinator shared by Vistoda entities."""

from datetime import timedelta

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .errors import BridgeError, ReauthRequiredError


class RingStatusCoordinator(DataUpdateCoordinator):
    """Poll one bounded status document instead of each entity separately."""

    def __init__(self, hass, client, alias: str, entry=None) -> None:
        super().__init__(
            hass,
            logger=__import__("logging").getLogger(__name__),
            name="Vistoda Ring native status",
            update_interval=timedelta(seconds=60),
            config_entry=entry,
        )
        self.client = client
        self.alias = alias

    async def _async_update_data(self):
        try:
            return await self.client.ring_status(self.alias)
        except ReauthRequiredError as error:
            # Home Assistant starts the existing reauth flow for the bound entry.
            raise ConfigEntryAuthFailed("Ring session requires a new login") from error
        except BridgeError as error:
            raise UpdateFailed("native Ring status check failed") from error
