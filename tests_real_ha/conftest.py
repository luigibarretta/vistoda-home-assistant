"""Real Home Assistant fixtures, deliberately separate from pure-client stubs."""

from unittest.mock import AsyncMock, patch

import pytest_asyncio
from aiohttp import ClientSession
from homeassistant.config_entries import ConfigEntries
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import frame


@pytest_asyncio.fixture
async def hass(tmp_path):
    instance = HomeAssistant(str(tmp_path))
    instance.config_entries = ConfigEntries(instance, {})
    frame.async_setup(instance)
    dr.async_setup(instance)
    await dr.async_load(instance)
    await er.async_load(instance)
    # A real local session avoids opening HA's multicast DNS/discovery services.
    async with ClientSession() as session:
        with patch("custom_components.media_bridge.async_get_clientsession", return_value=session):
            yield instance
            await instance.async_stop(force=True)


async def register_entry(hass, entry):
    """Register a real ConfigEntry without auto-starting unrelated HA components."""
    with patch.object(hass.config_entries, "async_setup", AsyncMock(return_value=True)):
        await hass.config_entries.async_add(entry)
