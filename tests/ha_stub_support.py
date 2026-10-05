"""Minimal Home Assistant doubles for connectivity, reauth and push-health tests."""

import enum
import importlib
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock


class AuthFailedError(Exception):
    pass


class UpdateFailedError(Exception):
    pass


class Coordinator:
    def __init__(self, hass, *, logger=None, name="", update_interval=None, config_entry=None):
        self.hass = hass
        self.config_entry = config_entry
        self.data = None
        self.last_update_success = True


class CoordinatorEntity:
    def __init__(self, coordinator):
        self.coordinator = coordinator


class Entity:
    _attr_available = True
    _attr_is_on = None
    _attr_extra_state_attributes = None
    unique_id = property(lambda self: self._attr_unique_id)
    device_info = property(lambda self: self._attr_device_info)
    available = property(lambda self: self._attr_available)
    is_on = property(lambda self: self._attr_is_on)
    extra_state_attributes = property(lambda self: self._attr_extra_state_attributes)

    async def async_added_to_hass(self):
        return None


class DeviceClass(enum.StrEnum):
    CONNECTIVITY = "connectivity"


def stub_ha(monkeypatch):
    """Register isolated HA doubles and return the shared issue registry mock."""

    def module(name, **values):
        result = ModuleType(name)
        result.__dict__.update(values)
        monkeypatch.setitem(sys.modules, name, result)
        return result

    issues = SimpleNamespace(async_create_issue=Mock(), async_delete_issue=Mock())
    ir = module(
        "homeassistant.helpers.issue_registry",
        async_create_issue=issues.async_create_issue,
        async_delete_issue=issues.async_delete_issue,
        IssueSeverity=SimpleNamespace(WARNING="warning", ERROR="error"),
    )
    registry = SimpleNamespace(
        entities={}, async_get=lambda _key: None, async_get_entity_id=lambda *_args: None
    )
    dr = module("homeassistant.helpers.device_registry", async_get=lambda _hass: registry)
    er = module("homeassistant.helpers.entity_registry", async_get=lambda _hass: registry)
    module("homeassistant")
    module("homeassistant.helpers", issue_registry=ir, device_registry=dr, entity_registry=er)
    module(
        "homeassistant.const",
        EVENT_HOMEASSISTANT_STOP="homeassistant_stop",
        STATE_UNAVAILABLE="unavailable",
        STATE_UNKNOWN="unknown",
    )
    module(
        "homeassistant.core",
        HomeAssistant=object,
        Event=object,
        State=object,
        callback=lambda func: func,
    )
    module("homeassistant.helpers.event", async_track_state_change_event=Mock())
    module("homeassistant.config_entries", ConfigEntry=object)
    module("homeassistant.exceptions", ConfigEntryAuthFailed=AuthFailedError)
    module(
        "homeassistant.helpers.dispatcher",
        async_dispatcher_send=Mock(),
        async_dispatcher_connect=Mock(),
    )
    module(
        "homeassistant.helpers.update_coordinator",
        DataUpdateCoordinator=Coordinator,
        UpdateFailed=UpdateFailedError,
        CoordinatorEntity=CoordinatorEntity,
    )
    module(
        "homeassistant.components.binary_sensor",
        BinarySensorDeviceClass=DeviceClass,
        BinarySensorEntity=Entity,
    )
    module(
        "homeassistant.helpers.entity",
        Entity=Entity,
        EntityCategory=SimpleNamespace(DIAGNOSTIC="diagnostic"),
    )
    module("homeassistant.helpers.entity_platform", AddConfigEntryEntitiesCallback=object)
    package = sys.modules["custom_components.media_bridge"]
    monkeypatch.setattr(package, "BridgeRuntime", SimpleNamespace, raising=False)
    return issues


def load(monkeypatch, name):
    """Import one integration module against the registered doubles only."""
    full = f"custom_components.media_bridge.{name}"
    monkeypatch.delitem(sys.modules, full, raising=False)
    imported = importlib.import_module(full)
    del sys.modules[full]
    monkeypatch.setitem(sys.modules, full, imported)
    return imported


def config_entry(provider="ring", entry_id="entry-1", **data):
    return SimpleNamespace(
        entry_id=entry_id,
        title="Front door",
        disabled_by=None,
        data={"provider": provider, "alias": "entrance", **data},
        async_start_reauth=Mock(),
    )
