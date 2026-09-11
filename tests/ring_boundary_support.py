"""Minimal HA registries for executable Ring boundary tests without a Core install."""

import importlib
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, Mock

from custom_components.media_bridge.ring_binding import (
    CONF_RING_DEVICE_ID,
    CONF_RING_OFFICIAL_BINDING,
)


class ValidationError(Exception):
    pass


class Runtime:
    def __init__(self, device_id, online=True):
        self.client = SimpleNamespace(
            ring_status=AsyncMock(return_value=SimpleNamespace(device_id=device_id, online=online)),
            unlock_ring=AsyncMock(),
        )
        self.ring_history = SimpleNamespace(async_record=AsyncMock())


def boundary(monkeypatch):
    def module(name, **values):
        result = ModuleType(name)
        result.__dict__.update(values)
        monkeypatch.setitem(sys.modules, name, result)
        return result

    module("voluptuous", Schema=lambda x: x, Optional=lambda x: x)
    module("homeassistant")
    module("homeassistant.const", STATE_UNAVAILABLE="unavailable", STATE_UNKNOWN="unknown")
    module(
        "homeassistant.core",
        HomeAssistant=object,
        ServiceCall=object,
        Event=object,
        State=object,
        callback=lambda f: f,
    )
    module("homeassistant.exceptions", ServiceValidationError=ValidationError)
    entity_registry = SimpleNamespace(entities={})
    device_registry = SimpleNamespace(async_get=lambda key: devices.get(key))
    er = module("homeassistant.helpers.entity_registry", async_get=lambda _: entity_registry)
    dr = module("homeassistant.helpers.device_registry", async_get=lambda _: device_registry)
    module("homeassistant.helpers", entity_registry=er, device_registry=dr)
    module("homeassistant.helpers.dispatcher", async_dispatcher_connect=Mock())
    module("homeassistant.helpers.entity", Entity=object)
    module("homeassistant.helpers.event", async_track_state_change_event=Mock())
    package = sys.modules["custom_components.media_bridge"]
    monkeypatch.setattr(package, "BridgeRuntime", Runtime, raising=False)
    entries, devices, runtimes = {}, {}, {}
    services = SimpleNamespace(async_call=AsyncMock(), async_register=Mock())
    hass = SimpleNamespace(
        config_entries=SimpleNamespace(
            async_entries=lambda _: list(entries.values()),
            async_get_entry=lambda key: entries.get(key),
            async_update_entry=Mock(),
        ),
        data={"media_bridge": runtimes},
        services=services,
        states=SimpleNamespace(get=lambda _: SimpleNamespace(state="available")),
        bus=SimpleNamespace(async_fire=Mock()),
        auth=SimpleNamespace(async_get_user=AsyncMock()),
    )
    # Register imported modules with monkeypatch so no fake HA dependency escapes the test.
    for name in ("ring_facade", "services"):
        full = f"custom_components.media_bridge.{name}"
        monkeypatch.delitem(sys.modules, full, raising=False)
        imported = importlib.import_module(full)
        del sys.modules[full]
        monkeypatch.setitem(sys.modules, full, imported)
    facade = sys.modules["custom_components.media_bridge.ring_facade"]
    service = sys.modules["custom_components.media_bridge.services"]
    service.async_register(hass)
    handle = services.async_register.call_args.args[2]

    def add_entry(key, device_id, *, online=True, loaded=True, alias="entrance"):
        entry = SimpleNamespace(
            entry_id=key,
            title=key,
            options={},
            data={
                "provider": "ring",
                "alias": alias,
                CONF_RING_DEVICE_ID: device_id,
                CONF_RING_OFFICIAL_BINDING: {
                    "device_id": f"official-{key}",
                    "config_entry_id": f"ring-{key}",
                    "unique_id": f"{device_id}-open_door",
                },
            },
        )
        entries[key] = entry
        if loaded:
            runtimes[key] = Runtime(device_id, online)
        return entry

    def add_official(key, device_id):
        entity_id = f"button.official_{key}"
        entity_registry.entities[entity_id] = SimpleNamespace(
            entity_id=entity_id,
            platform="ring",
            device_id=f"official-{key}",
            config_entry_id=f"ring-{key}",
            unique_id=f"{device_id}-open_door",
            disabled_by=None,
            translation_key="open_door",
            original_name="Open door",
        )
        devices[f"official-{key}"] = SimpleNamespace(manufacturer="Ring", model="Intercom")
        return entity_id

    return SimpleNamespace(
        hass=hass,
        entries=entries,
        runtimes=runtimes,
        handle=handle,
        add_entry=add_entry,
        add_official=add_official,
        registry=entity_registry,
        facade=facade,
    )


def call(entry_id=None, user_id=None):
    return SimpleNamespace(
        data={} if entry_id is None else {"entry_id": entry_id},
        context=SimpleNamespace(user_id=user_id),
    )
