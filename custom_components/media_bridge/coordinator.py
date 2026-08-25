"""Availability coordinator for one bridge entry."""

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import BridgeClient
from .errors import BridgeError
from .repairs import update_bridge_issue


class BridgeCoordinator(DataUpdateCoordinator[str]):
    """Poll only minimal health; media remains on demand."""

    def __init__(self, hass, client: BridgeClient, entry: ConfigEntry, name: str) -> None:
        super().__init__(
            hass,
            logger=__import__("logging").getLogger(__name__),
            name=name,
            update_interval=timedelta(seconds=60),
        )
        self.client = client
        self.entry = entry

    async def _async_update_data(self) -> str:
        try:
            version = (await self.client.health()).version
        except BridgeError as error:
            update_bridge_issue(self.hass, self.entry, available=False)
            raise UpdateFailed("bridge health check failed") from error
        update_bridge_issue(self.hass, self.entry, available=True)
        return version
