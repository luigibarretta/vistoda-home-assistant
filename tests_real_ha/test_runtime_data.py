"""ConfigEntry.runtime_data through Home Assistant's own entry setup and unload."""

from contextlib import ExitStack, contextmanager
from types import MappingProxyType, SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant import loader
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.exceptions import ServiceValidationError

import custom_components
from custom_components import media_bridge
from custom_components.media_bridge import (
    diagnostics,
    ezviz_alarm_api,
    provider_recording_websocket,
    ring_audio_proxy,
    services,
    websocket,
)
from custom_components.media_bridge.const import DOMAIN
from custom_components.media_bridge.models import RingStatus
from custom_components.media_bridge.runtime import BridgeRuntime, runtime_for

from .conftest import register_entry

RING_STATUS = RingStatus(
    battery=80,
    online=True,
    doorbell_volume=5,
    mic_volume=5,
    voice_volume=5,
    last_activity=None,
    device_id="42",
)


def make(provider, alias, domain=DOMAIN, **data):
    return ConfigEntry(
        domain=domain,
        title=f"Vistoda {provider}",
        data={
            "provider": provider,
            "alias": alias,
            "url": "http://127.0.0.1:9",
            "api_token": "fixture-token-never-sent",
            **data,
        },
        source="user",
        version=1,
        minor_version=1,
        unique_id=f"{provider}:{alias}",
        options={},
        discovery_keys=MappingProxyType({}),
        subentries_data=None,
    )


@contextmanager
def offline_bridges(hass):
    """Answer every bridge call in memory; listeners never open a socket."""
    client = media_bridge.BridgeClient
    calls = SimpleNamespace(ring_start=Mock(), ring_stop=AsyncMock(), ezviz_start=Mock())
    with ExitStack() as stack:
        for target, name, value in (
            (client, "health", AsyncMock(return_value=SimpleNamespace(version="fixture"))),
            (client, "ezviz_camera_identity", AsyncMock(return_value="FIXTURE123:1")),
            (client, "ring_status", AsyncMock(return_value=RING_STATUS)),
            (media_bridge.RingEventListener, "start", calls.ring_start),
            (media_bridge.RingEventListener, "stop", calls.ring_stop),
            (media_bridge.EzvizAlarmListener, "start", calls.ezviz_start),
            (media_bridge.EzvizAlarmListener, "stop", AsyncMock()),
            (media_bridge.RingHistoryManager, "async_warm_provider", AsyncMock()),
            (hass.config_entries, "async_forward_entry_setups", AsyncMock()),
            (hass.config_entries, "async_unload_platforms", AsyncMock(return_value=True)),
        ):
            stack.enter_context(patch.object(target, name, value))
        # The fixture HA has no custom-component loader; these only read the manifest.
        for name, value in (("support_entry_unload", True), ("support_remove_from_device", False)):
            stack.enter_context(
                patch(f"homeassistant.config_entries.{name}", AsyncMock(return_value=value))
            )
        yield calls


@pytest.fixture
def integration(hass):
    loader.async_setup(hass)
    return loader.Integration.resolve_from_root(hass, custom_components, DOMAIN)


async def setup(hass, entry, integration):
    async with entry.setup_lock:
        await entry.async_setup(hass, integration=integration)
    return entry.state


async def unload(hass, entry, integration):
    async with entry.setup_lock:
        return await entry.async_unload(hass, integration=integration)


def leftovers(hass, entry_id):
    """Every hass.data[DOMAIN] slot that still names the entry."""
    data = hass.data.get(DOMAIN, {})
    return [key for key, value in data.items() if key == entry_id or entry_id in str(value)]


async def test_unload_then_reload_rebuilds_runtime_and_leaves_nothing(hass, integration):
    entry = make("ezviz", "front", ezviz_source_id="FIXTURE123:1")
    await register_entry(hass, entry)
    with offline_bridges(hass) as calls:
        assert await setup(hass, entry, integration) is ConfigEntryState.LOADED
        first = entry.runtime_data
        assert isinstance(first, BridgeRuntime) and first.ezviz_alarms is not None
        assert runtime_for(hass, entry.entry_id) is first
        assert await unload(hass, entry, integration)
        assert entry.state is ConfigEntryState.NOT_LOADED
        assert not hasattr(entry, "runtime_data")
        assert runtime_for(hass, entry.entry_id) is None
        assert leftovers(hass, entry.entry_id) == []
        assert await setup(hass, entry, integration) is ConfigEntryState.LOADED
        assert entry.runtime_data is not first and entry.runtime_data.client is not first.client
        assert calls.ezviz_start.call_count == 2
        assert await unload(hass, entry, integration)
    assert leftovers(hass, entry.entry_id) == []


async def test_ring_and_ezviz_entries_keep_separate_runtimes(hass, integration):
    ring = make("ring", "entrance")
    ezviz = make("ezviz", "front", ezviz_source_id="FIXTURE123:1")
    for entry in (ring, ezviz):
        await register_entry(hass, entry)
    with offline_bridges(hass) as calls:
        for entry in (ring, ezviz):
            assert await setup(hass, entry, integration) is ConfigEntryState.LOADED
        assert ring.runtime_data is not ezviz.runtime_data
        assert ring.runtime_data.ring_status.data.device_id == "42"
        assert ring.runtime_data.ring_events is not None and ring.runtime_data.ezviz_media is None
        assert ezviz.runtime_data.ezviz_media is not None and ezviz.runtime_data.ring_status is None
        assert websocket.resolve_ring(hass, ring.entry_id) == (ring.runtime_data, "entrance")
        assert websocket.resolve_ring(hass, ezviz.entry_id) is None
        assert ezviz_alarm_api.resolve(hass, ezviz.entry_id) == (ezviz, ezviz.runtime_data)
        assert ezviz_alarm_api.resolve(hass, ring.entry_id) is None
        assert await unload(hass, ring, integration)
        calls.ring_stop.assert_awaited_once()
        assert not hasattr(ring, "runtime_data") and leftovers(hass, ring.entry_id) == []
        assert ezviz.state is ConfigEntryState.LOADED
        assert provider_recording_websocket._resolve(hass, ezviz.entry_id) == (
            ezviz.runtime_data,
            "front",
        )
        assert await unload(hass, ezviz, integration)


async def test_views_services_and_diagnostics_see_a_not_loaded_entry_as_before(hass, integration):
    ring = make("ring", "entrance", ring_device_id="42")
    ezviz = make("ezviz", "front", ezviz_source_id="FIXTURE123:1")
    for entry in (ring, ezviz):
        await register_entry(hass, entry)
    services.async_register(hass)
    for _ in range(2):  # Never set up, then set up and unloaded again.
        assert websocket.resolve_ring(hass, ring.entry_id) is None
        assert ring_audio_proxy.resolve_ring(hass, ring.entry_id) is None
        assert ezviz_alarm_api.resolve(hass, ezviz.entry_id) is None
        assert provider_recording_websocket._resolve(hass, ezviz.entry_id) is None
        with pytest.raises(ServiceValidationError, match="not loaded"):
            await hass.services.async_call(
                DOMAIN, "open_ring_door", {"entry_id": ring.entry_id}, blocking=True
            )
        payload = await diagnostics.async_get_config_entry_diagnostics(hass, ezviz)
        assert payload["loaded"] is False and payload["coordinator"]["data_kind"] == "none"
        with offline_bridges(hass):
            for entry in (ring, ezviz):
                assert await setup(hass, entry, integration) is ConfigEntryState.LOADED
            payload = await diagnostics.async_get_config_entry_diagnostics(hass, ezviz)
            assert payload["loaded"] is True
            for entry in (ring, ezviz):
                assert await unload(hass, entry, integration)
    # Unknown ids, non-string ids and another integration's runtime_data never resolve.
    other = make("ring", "official", domain="ring")
    await register_entry(hass, other)
    other.runtime_data = object()
    for entry_id in ("missing", None, 7, other.entry_id):
        assert runtime_for(hass, entry_id) is None
