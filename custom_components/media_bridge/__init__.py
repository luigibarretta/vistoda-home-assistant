"""Vistoda integration setup."""

from dataclasses import dataclass

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import BridgeClient
from .const import (
    CONF_API_TOKEN,
    CONF_DISCOVERY_TOKENS,
    CONF_LINKED_DEVICE_IDS,
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
                ),
                vol.Optional(CONF_LINKED_DEVICE_IDS, default={}): vol.Schema(
                    {vol.Optional(PROVIDER_RING): cv.string}
                ),
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
    linked_identifiers: set[tuple[str, str]] | None = None
    panel_url: str | None = None


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Load optional secret bootstrap tokens for zero-copy discovery."""
    from .panel import async_register as async_register_panel
    from .websocket import async_register as async_register_websocket

    settings = config.get(DOMAIN, {})
    hass.data.setdefault(DOMAIN, {})[CONF_DISCOVERY_TOKENS] = settings.get(
        CONF_DISCOVERY_TOKENS, {}
    )
    hass.data[DOMAIN][CONF_LINKED_DEVICE_IDS] = settings.get(CONF_LINKED_DEVICE_IDS, {})
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
    linked_identifiers = _linked_identifiers(hass, provider)
    base_url = hass.config.external_url or hass.config.internal_url
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = BridgeRuntime(
        client=client,
        coordinator=coordinator,
        linked_identifiers=linked_identifiers,
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


def _linked_identifiers(hass: HomeAssistant, provider: str) -> set[tuple[str, str]] | None:
    """Resolve an explicitly approved provider device without fuzzy matching."""
    linked = hass.data[DOMAIN].get(CONF_LINKED_DEVICE_IDS, {}).get(provider)
    if not linked:
        return None
    device = dr.async_get(hass).async_get(linked)
    entries = (
        [hass.config_entries.async_get_entry(item) for item in device.config_entries]
        if device
        else []
    )
    if (
        device is None
        or not device.identifiers
        or not any(item is not None and item.domain == provider for item in entries)
    ):
        raise ConfigEntryNotReady(f"approved {provider} device link is invalid")
    return set(device.identifiers)
