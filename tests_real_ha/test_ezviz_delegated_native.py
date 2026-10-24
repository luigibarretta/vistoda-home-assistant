"""Delegated EZVIZ through real registries, states and services, never runtime objects."""

from types import MappingProxyType, SimpleNamespace
from unittest.mock import Mock

import pytest
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import Context
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from custom_components.media_bridge import ezviz_core
from custom_components.media_bridge import ezviz_settings_websocket as settings

from .conftest import register_entry

SERIAL = "BC1234567"
CAMERA = "camera.front_door"


def make(domain, unique_id, data, options=None):
    return ConfigEntry(
        domain=domain,
        title=unique_id,
        data=data,
        source="user",
        version=1,
        minor_version=1,
        unique_id=unique_id,
        options=options or {},
        discovery_keys=MappingProxyType({}),
        subentries_data=None,
    )


class OfficialEntry(ConfigEntry):
    """The official EZVIZ entry; Vistoda must never read its runtime objects."""

    @property
    def runtime_data(self):
        raise AssertionError("runtime_data belongs to the official EZVIZ integration")

    @runtime_data.setter
    def runtime_data(self, _value):
        return None


async def official(hass, *, poll_applies=True):
    """Register the official EZVIZ entry, device, camera entity, state and services."""
    native = make("ezviz", "account", {"type": "EZVIZ_CLOUD_ACCOUNT"})
    native.__class__ = OfficialEntry
    await register_entry(hass, native)
    native._async_set_state(hass, ConfigEntryState.LOADED, None)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=native.entry_id, identifiers={("ezviz", SERIAL)}, name="Front door"
    )
    er.async_get(hass).async_get_or_create(
        "camera",
        "ezviz",
        SERIAL,
        config_entry=native,
        device_id=device.id,
        suggested_object_id="front_door",
    )
    cloud = {"motion_detection": False}
    hass.states.async_set(CAMERA, "idle", {})
    calls = []

    async def set_defence(call):
        calls.append((call.service, call.context.id))
        cloud["motion_detection"] = call.service == "enable_motion_detection"

    async def poll(_call):
        if poll_applies:
            attributes = {"motion_detection": True} if cloud["motion_detection"] else {}
            hass.states.async_set(CAMERA, "idle", attributes)

    for service in ("enable_motion_detection", "disable_motion_detection"):
        hass.services.async_register("camera", service, set_defence)
    hass.services.async_register("homeassistant", "update_entity", poll)
    vistoda = make(
        "media_bridge",
        "ezviz:front",
        {"provider": "ezviz", "alias": "front", "ezviz_source_id": f"{SERIAL}:1"},
        {"ezviz_delegate_controls": True},
    )
    await register_entry(hass, vistoda)
    return vistoda, calls


def connection():
    return SimpleNamespace(
        user=SimpleNamespace(is_admin=True),
        send_result=Mock(),
        send_error=Mock(),
        async_handle_exception=Mock(),
        context=lambda _msg: Context(id="panel-user"),
    )


async def call(hass, handler, msg):
    conn = connection()
    handler(hass, conn, {"id": 7, **msg})
    await hass.async_block_till_done(wait_background_tasks=True)
    return conn


def arm(entry):
    return {
        "entry_id": entry.entry_id,
        "key": "camera_defence",
        "value": True,
        "expected_value": False,
    }


async def test_arming_goes_through_official_services_and_published_state(hass):
    entry, calls = await official(hass)
    assert ezviz_core.native_camera_online(hass, entry) is True
    conn = await call(hass, settings.ws_settings_set, arm(entry))
    armed = {"key": "camera_defence", "group": "arming", "kind": "boolean", "value": True}
    conn.send_result.assert_called_once_with(7, {"settings": [armed], "source": "native"})
    assert calls == [("enable_motion_detection", "panel-user")]
    conn = await call(hass, settings.ws_settings_info, {"entry_id": entry.entry_id})
    conn.send_result.assert_called_once_with(7, {"settings": [armed], "source": "native"})
    hass.states.async_set(CAMERA, "unavailable", {})
    assert ezviz_core.native_camera_online(hass, entry) is False


async def test_a_write_the_official_state_never_shows_is_unconfirmed(hass, monkeypatch):
    monkeypatch.setattr(settings, "CONFIRM_TIMEOUT", 0.05)
    entry, calls = await official(hass, poll_applies=False)
    conn = await call(hass, settings.ws_settings_set, arm(entry))
    assert conn.send_error.call_args.args[1] == "unconfirmed"
    assert calls == [("enable_motion_detection", "panel-user")]


@pytest.mark.parametrize("state", [ConfigEntryState.SETUP_RETRY, ConfigEntryState.NOT_LOADED])
async def test_an_official_entry_that_is_not_loaded_serves_nothing(hass, state):
    entry, _calls = await official(hass)
    native = hass.config_entries.async_entries("ezviz")[0]
    native._async_set_state(hass, state, None)
    assert not ezviz_core.native_controls_available(hass, entry)
    assert ezviz_core.native_camera_online(hass, entry) is None
