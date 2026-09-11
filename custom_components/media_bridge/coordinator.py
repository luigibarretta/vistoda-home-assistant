"""Availability coordinator for one bridge entry."""

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import BridgeClient
from .const import CONF_PROVIDER, PROVIDER_EZVIZ
from .errors import BridgeError
from .repairs import update_bridge_issue, update_ezviz_binding_issue


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
            if self.entry.data.get(CONF_PROVIDER) == PROVIDER_EZVIZ:
                update_ezviz_binding_issue(self.hass, self.entry, available=True)
            raise UpdateFailed("bridge health check failed") from error
        update_bridge_issue(self.hass, self.entry, available=True)
        if self.entry.data.get(CONF_PROVIDER) == PROVIDER_EZVIZ:
            from .ezviz_binding import CONF_EZVIZ_SOURCE_ID, async_verify_native

            try:
                if CONF_EZVIZ_SOURCE_ID in self.entry.data:
                    await async_verify_native(self.entry, self.client)
            except BridgeError as error:
                update_ezviz_binding_issue(self.hass, self.entry, available=False)
                raise UpdateFailed("EZVIZ physical camera identity changed") from error
            update_ezviz_binding_issue(self.hass, self.entry, available=True)
        return version
