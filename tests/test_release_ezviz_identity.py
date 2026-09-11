"""Non-destructive EZVIZ namespacing with duplicate aliases and shared devices."""

from types import SimpleNamespace

import pytest
from release_flow_support import entry, framework

from custom_components.media_bridge import ezviz_identity as identity


def registry_environment(monkeypatch, shared=False):
    env = framework(monkeypatch)
    configured = entry("ezviz")
    device = SimpleNamespace(
        id="old-device",
        identifiers={("media_bridge", "ezviz:entrance")},
        config_entries={"entry-a", "other"} if shared else {"entry-a"},
        name_by_user="My camera",
        area_id="hall",
    )
    entities = {
        "camera.entry": SimpleNamespace(
            entity_id="camera.entry",
            unique_id="ezviz-entrance-bridge-camera",
            config_entry_id="entry-a",
            platform="media_bridge",
            domain="camera",
            device_id="old-device",
        ),
        "camera.other": SimpleNamespace(
            entity_id="camera.other",
            unique_id="unrelated",
            config_entry_id="other",
            platform="media_bridge",
            domain="camera",
            device_id="old-device",
        ),
    }
    changes = []

    def update(entity_id, **kwargs):
        changes.append((entity_id, kwargs))
        for key, value in kwargs.items():
            setattr(entities[entity_id], "unique_id" if key == "new_unique_id" else key, value)

    er = SimpleNamespace(
        entities=entities,
        async_update_entity=update,
        async_get_entity_id=lambda domain, platform, unique_id: next(
            (item.entity_id for item in entities.values() if item.unique_id == unique_id), None
        ),
    )
    device_changes = []
    dr = SimpleNamespace(
        async_get_device_by_identifier=lambda identifier, entry_id: device,
        async_update_device=lambda device_id, **kwargs: device_changes.append((device_id, kwargs)),
        async_get_or_create=lambda **kwargs: SimpleNamespace(id="new-device"),
    )
    entity_module = env.module("homeassistant.helpers.entity_registry", async_get=lambda hass: er)
    device_module = env.module("homeassistant.helpers.device_registry", async_get=lambda hass: dr)
    env.module(
        "homeassistant.helpers", entity_registry=entity_module, device_registry=device_module
    )
    return env, configured, er, changes, device_changes


def test_same_alias_is_namespaced_by_entry_and_legacy_entity_id_is_preserved(monkeypatch):
    env, configured, registry, _changes, devices = registry_environment(monkeypatch)
    identity.async_migrate_registry(env.hass, configured)
    assert registry.entities["camera.entry"].unique_id == "ezviz-entry-a-bridge-camera"
    assert registry.entities["camera.other"].unique_id == "unrelated"
    assert devices == [("old-device", {"new_identifiers": {("media_bridge", "ezviz:entry-a")}})]
    assert identity.device_identifier(configured) != identity.device_identifier(
        entry("ezviz", "entry-b")
    )


def test_shared_legacy_device_is_split_only_for_its_entry(monkeypatch):
    env, configured, registry, _changes, devices = registry_environment(monkeypatch, shared=True)
    identity.async_migrate_registry(env.hass, configured)
    assert registry.entities["camera.entry"].device_id == "new-device"
    assert registry.entities["camera.other"].device_id == "old-device"
    assert ("old-device", {"remove_config_entry_id": "entry-a"}) in devices
    assert ("new-device", {"name_by_user": "My camera", "area_id": "hall"}) in devices


def test_migration_collision_fails_before_any_registry_mutation(monkeypatch):
    env, configured, registry, changes, devices = registry_environment(monkeypatch)
    registry.entities["camera.other"].unique_id = "ezviz-entry-a-bridge-camera"
    with pytest.raises(ValueError, match="collision"):
        identity.async_migrate_registry(env.hass, configured)
    assert changes == [] and devices == []
