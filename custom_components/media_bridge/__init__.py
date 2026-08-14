"""Vistoda integration setup."""

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import BridgeClient
from .const import CONF_API_TOKEN, CONF_PROVIDER, CONF_URL, DOMAIN, PLATFORMS
from .coordinator import BridgeCoordinator


@dataclass(slots=True)
class BridgeRuntime:
    """Runtime owned by one config entry."""

    client: BridgeClient
    coordinator: BridgeCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Create the bounded bridge client and entities."""
    client = BridgeClient(
        async_get_clientsession(hass),
        entry.data[CONF_URL],
        entry.data[CONF_API_TOKEN],
    )
    coordinator = BridgeCoordinator(hass, client, f"Vistoda {entry.data[CONF_PROVIDER]} bridge")
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = BridgeRuntime(
        client=client, coordinator=coordinator
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload entities and drop the client reference."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    hass.data[DOMAIN].pop(entry.entry_id, None)
    return True
