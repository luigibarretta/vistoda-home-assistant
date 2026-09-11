"""Entry and physical-device isolation for history and registry migrations."""

import importlib
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from ring_boundary_support import boundary

from custom_components.media_bridge.client_ring_history import (
    RingHistoryEvent,
    RingHistoryIdentity,
    RingHistoryPage,
)
from custom_components.media_bridge.ring_binding import async_migrate_registry


@pytest.mark.asyncio
async def test_history_isolated_by_entry_and_rejects_retargeted_provider(monkeypatch):
    env = boundary(monkeypatch)
    first, second = env.add_entry("a", "42"), env.add_entry("b", "43")
    storage = ModuleType("homeassistant.helpers.storage")

    class Store:
        def __class_getitem__(cls, _):
            return cls

        def __init__(self, _hass, _version, key, **_kwargs):
            self.key = key
            self.async_load = AsyncMock(return_value=None)
            self.async_save = AsyncMock()

    storage.Store = Store
    monkeypatch.setitem(sys.modules, storage.__name__, storage)
    util = ModuleType("homeassistant.util")
    util.dt = SimpleNamespace(as_local=lambda value: value)
    monkeypatch.setitem(sys.modules, util.__name__, util)
    name = "custom_components.media_bridge.ring_history"
    monkeypatch.delitem(sys.modules, name, raising=False)
    history = importlib.import_module(name)
    del sys.modules[name]
    monkeypatch.setitem(sys.modules, name, history)
    monkeypatch.setattr(
        history,
        "home_assistant_identity",
        lambda *_: {
            "device_name": "HA",
            "location_name": "Home",
            "city": "",
        },
    )

    def client(device_id):
        return SimpleNamespace(
            ring_history=AsyncMock(
                return_value=RingHistoryPage(
                    RingHistoryIdentity(f"Device {device_id}", "Home", None, device_id),
                    (RingHistoryEvent(f"event-{device_id}", "ding", 100),),
                    None,
                )
            )
        )

    a = history.RingHistoryManager(env.hass, first, client("42"), "entrance")
    b = history.RingHistoryManager(env.hass, second, client("43"), "entrance")
    assert a._store.key != b._store.key
    await a.async_record("unlock", 200, "command:test")
    page_a = await a.async_page(20, None)
    page_b = await b.async_page(20, None)
    assert page_a["entry_id"] == "a" and page_b["entry_id"] == "b"
    assert {item["event_type"] for item in page_a["events"]} == {"unlock", "ding"}
    assert [item["event_id"] for item in page_b["events"]] == ["event-43"]
    b.client = client("42")
    rejected = await b.async_page(20, None)
    assert rejected["degraded"] and rejected["events"] == []
    assert rejected["identity"]["device_name"] == "Device 43"


def test_registry_migration_preserves_entity_ids_and_other_entry(monkeypatch):
    env = boundary(monkeypatch)
    entry = env.add_entry("a", "42")
    first = SimpleNamespace(
        entity_id="button.original",
        config_entry_id="a",
        unique_id="ring-entrance-facade-open_door",
        device_id="shared",
    )
    second = SimpleNamespace(
        entity_id="button.other",
        config_entry_id="b",
        unique_id="ring-entrance-facade-open_door",
        device_id="shared",
    )
    env.registry.entities.update(first=first, second=second)
    env.registry.async_update_entity = Mock()
    original = SimpleNamespace(
        id="shared",
        config_entries={"a", "b"},
        identifiers={("media_bridge", "ring:entrance")},
        name="Ring",
        name_by_user="Front",
    )
    devices = SimpleNamespace(
        async_get_device_by_identifier=Mock(return_value=original),
        async_get_or_create=Mock(return_value=SimpleNamespace(id="isolated-a")),
        async_update_device=Mock(),
    )
    monkeypatch.setattr(env.facade.dr, "async_get", lambda _: devices)
    async_migrate_registry(env.hass, entry)
    calls = env.registry.async_update_entity.call_args_list
    assert all(call.args[0] == "button.original" for call in calls)
    assert calls[0].kwargs["new_unique_id"] == "ring-a-facade-open_door"
    assert calls[1].kwargs["device_id"] == "isolated-a"
    devices.async_update_device.assert_called_once_with("shared", remove_config_entry_id="a")
