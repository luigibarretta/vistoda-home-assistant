"""Version-matrix contracts using installed HA, never substitute HA classes."""

import importlib
import pkgutil
from types import MappingProxyType, SimpleNamespace
from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import ConfigEntry, ConfigEntryState, current_entry
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from custom_components import media_bridge
from custom_components.media_bridge.camera import EzvizBridgeCamera
from custom_components.media_bridge.config_flow import ConfigFlow
from custom_components.media_bridge.const import DOMAIN
from custom_components.media_bridge.ezviz_identity import device_identifier, entity_prefix

from .conftest import register_entry


def test_all_integration_modules_import_with_real_home_assistant():
    assert media_bridge.__file__.endswith("media_bridge/__init__.py")
    for module in pkgutil.iter_modules(media_bridge.__path__):
        if not module.ispkg:
            importlib.import_module(f"{media_bridge.__name__}.{module.name}")


def make_entry():
    return ConfigEntry(
        domain=DOMAIN,
        title="Vistoda fixture",
        data={
            "provider": "ezviz",
            "alias": "fixture",
            "url": "http://127.0.0.1:9",
            "api_token": "fixture-token-never-sent",
        },
        source="user",
        state=ConfigEntryState.SETUP_IN_PROGRESS,
        version=1,
        minor_version=1,
        unique_id="ezviz:fixture",
        options={},
        discovery_keys=MappingProxyType({}),
        subentries_data=None,
    )


async def test_real_setup_registry_migration_camera_and_unload(hass):
    entry = make_entry()
    await register_entry(hass, entry)
    devices = dr.async_get(hass)
    entities = er.async_get(hass)
    old_device = devices.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, "ezviz:fixture")},
        name="Fixture camera",
    )
    old_entity = entities.async_get_or_create(
        "camera",
        DOMAIN,
        "ezviz-fixture-bridge-camera",
        config_entry=entry,
        device_id=old_device.id,
        suggested_object_id="existing_fixture",
    )
    health = AsyncMock(return_value=SimpleNamespace(version="fixture-version"))
    with (
        patch.object(media_bridge.BridgeClient, "health", health),
        patch.object(hass.config_entries, "async_forward_entry_setups", AsyncMock()) as forward,
        current_entry.set(entry),
    ):
        assert await media_bridge.async_setup_entry(hass, entry)
    forward.assert_awaited_once()
    assert health.await_count == 1
    runtime = hass.data[DOMAIN][entry.entry_id]
    assert runtime.coordinator.last_update_success
    assert runtime.coordinator.data == "fixture-version"
    migrated = entities.async_get(old_entity.entity_id)
    assert migrated.unique_id == f"{entity_prefix(entry)}bridge-camera"
    assert device_identifier(entry) in devices.async_get(old_device.id).identifiers
    camera = EzvizBridgeCamera(runtime, entry)
    assert camera.unique_id == migrated.unique_id
    assert await camera.async_camera_image() is None
    with patch.object(
        hass.config_entries, "async_unload_platforms", AsyncMock(return_value=True)
    ) as unload:
        assert await media_bridge.async_unload_entry(hass, entry)
    unload.assert_awaited_once()
    assert entry.entry_id not in hass.data[DOMAIN]
    assert entities.async_get(old_entity.entity_id).entity_id == old_entity.entity_id


async def test_real_config_flow_uses_ha_forms_and_provider_validation(hass):
    flow = ConfigFlow()
    flow.hass = hass
    flow.context = {"source": "user"}
    result = await flow.async_step_user()
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["data_schema"]({"provider": "ezviz"}) == {"provider": "ezviz"}
    result = await flow.async_step_user({"provider": "ezviz"})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "bridge"
