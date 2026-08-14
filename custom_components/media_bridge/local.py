"""Local Vistoda adapters that deliberately reuse Home Assistant state."""

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import BLINK_BRIDGE_DOMAIN


class BlinkAdapterCoordinator(DataUpdateCoordinator[str]):
    """Report the loaded Blink relay without creating a second login."""

    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(hass, name="Vistoda Blink adapter", update_interval=None)

    async def _async_update_data(self) -> str:
        runtime: Any = self.hass.data.get(BLINK_BRIDGE_DOMAIN, {}).get("runtime")
        if runtime is None or not runtime.cameras:
            raise ConfigEntryNotReady("Blink Live Bridge is not loaded")
        return f"{len(runtime.cameras)} cameras"


def blink_adapter_available(hass: HomeAssistant) -> bool:
    """Return whether the existing local relay is ready for adoption."""
    runtime: Any = hass.data.get(BLINK_BRIDGE_DOMAIN, {}).get("runtime")
    return runtime is not None and bool(runtime.cameras)
