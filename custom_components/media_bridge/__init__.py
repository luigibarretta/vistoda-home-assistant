"""Vistoda integration setup."""

from dataclasses import dataclass

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import BridgeClient
from .const import (
    CONF_API_TOKEN,
    CONF_DISCOVERY_TOKENS,
    CONF_PROVIDER,
    CONF_URL,
    DOMAIN,
    PLATFORMS,
    PROVIDER_BLINK,
    PROVIDER_EZVIZ,
    PROVIDER_RING,
)
from .coordinator import BridgeCoordinator
from .local import BlinkAdapterCoordinator

CONFIG_SCHEMA = vol.Schema(
    {
        vol.Optional(DOMAIN): vol.Schema(
            {
                vol.Optional(CONF_DISCOVERY_TOKENS, default={}): vol.Schema(
                    {
                        vol.Optional(PROVIDER_EZVIZ): cv.string,
                        vol.Optional(PROVIDER_RING): cv.string,
                    }
                )
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


@dataclass(slots=True)
class BridgeRuntime:
    """Runtime owned by one config entry."""

    client: BridgeClient | None
    coordinator: BridgeCoordinator | BlinkAdapterCoordinator


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Load optional secret bootstrap tokens for zero-copy discovery."""
    settings = config.get(DOMAIN, {})
    hass.data.setdefault(DOMAIN, {})[CONF_DISCOVERY_TOKENS] = settings.get(
        CONF_DISCOVERY_TOKENS, {}
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Create the bounded bridge client and entities."""
    if entry.data[CONF_PROVIDER] == PROVIDER_BLINK:
        client = None
        coordinator = BlinkAdapterCoordinator(hass)
    else:
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
