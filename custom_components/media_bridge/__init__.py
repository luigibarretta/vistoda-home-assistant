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
    panel_url: str | None = None


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Load optional secret bootstrap tokens for zero-copy discovery."""
    from .panel import async_register as async_register_panel
    from .websocket import async_register as async_register_websocket

    settings = config.get(DOMAIN, {})
    hass.data.setdefault(DOMAIN, {})[CONF_DISCOVERY_TOKENS] = settings.get(
        CONF_DISCOVERY_TOKENS, {}
    )
    await async_register_panel(hass)
    async_register_websocket(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Create the bounded bridge client and entities."""
    provider = entry.data[CONF_PROVIDER]
    if provider == PROVIDER_BLINK:
        client = None
        coordinator = BlinkAdapterCoordinator(hass)
    else:
        client = BridgeClient(
            async_get_clientsession(hass),
            entry.data[CONF_URL],
            entry.data[CONF_API_TOKEN],
        )
        coordinator = BridgeCoordinator(hass, client, f"Vistoda {provider} bridge")
    await coordinator.async_config_entry_first_refresh()
    base_url = hass.config.external_url or hass.config.internal_url
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = BridgeRuntime(
        client=client,
        coordinator=coordinator,
        panel_url=f"{base_url.rstrip('/')}/vistoda-ring" if base_url else None,
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload entities and drop the client reference."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    hass.data[DOMAIN].pop(entry.entry_id, None)
    return True
