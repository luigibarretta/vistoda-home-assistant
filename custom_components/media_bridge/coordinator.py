"""Availability coordinator for one bridge entry."""

from datetime import timedelta

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import BridgeClient
from .errors import BridgeError


class BridgeCoordinator(DataUpdateCoordinator[str]):
    """Poll only minimal health; media remains on demand."""

    def __init__(self, hass, client: BridgeClient, name: str) -> None:
        super().__init__(
            hass,
            logger=__import__("logging").getLogger(__name__),
            name=name,
            update_interval=timedelta(seconds=60),
        )
        self.client = client

    async def _async_update_data(self) -> str:
        try:
            return (await self.client.health()).version
        except BridgeError as error:
            raise UpdateFailed("bridge health check failed") from error
