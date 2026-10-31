"""EZVIZ media coordinator, microSD entities, panel metadata and SD-record command."""

import sys
from datetime import date
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, Mock

import ha_stub_support
import pytest
from ha_stub_support import Entity, UpdateFailedError, bind_runtime, config_entry, load, stub_ha

from custom_components.media_bridge.client_ezviz_media import (
    EzvizEncryption,
    EzvizFeatureUnsupportedError,
    EzvizSdRecord,
    EzvizStorage,
)
from custom_components.media_bridge.errors import CannotConnectError

SOURCE = "SERIAL1:1"


def ezviz_entry():
    return config_entry("ezviz", "01J9ENTRY", alias="front-door", ezviz_source_id=SOURCE)


def stub_modules(monkeypatch, **extra):
    stub_ha(monkeypatch)
    modules = {
        "homeassistant.components.sensor": {
            "SensorEntity": Entity,
            "SensorDeviceClass": SimpleNamespace(ENUM="enum"),
        },
        "homeassistant.util.dt": {"now": lambda: SimpleNamespace(date=lambda: date(2026, 10, 4))},
        **extra,
    }
    for name, values in modules.items():
        module = ModuleType(name)
        module.__dict__.update(values)
        monkeypatch.setitem(sys.modules, name, module)
    binary = sys.modules["homeassistant.components.binary_sensor"]
    binary.BinarySensorDeviceClass = SimpleNamespace(PROBLEM="problem", CONNECTIVITY="connectivity")


def media_client(encryption=None, storage=None):
    return SimpleNamespace(
        ezviz_encryption=AsyncMock(side_effect=[encryption]),
        ezviz_storage=AsyncMock(side_effect=[storage]),
    )


async def test_coordinator_reports_partial_support_and_fails_closed(monkeypatch) -> None:
    stub_modules(monkeypatch)
    media = load(monkeypatch, "ezviz_media")
    bridge = SimpleNamespace(last_update_success=True)
    client = media_client(EzvizEncryption(True, "none"), EzvizFeatureUnsupportedError())
    coordinator = media.EzvizMediaCoordinator(None, ezviz_entry(), client, bridge)
    status = await coordinator._async_update_data()
    assert status == media.EzvizMediaStatus(EzvizEncryption(True, "none"), None)
    assert not media.reports_storage(status)
    assert media.media_payload(status) == {
        "encryption": {"video_encrypted": True, "key_source": "none"},
        "storage": None,
    }
    client.ezviz_storage.assert_awaited_once_with("front-door")
    client.ezviz_encryption.side_effect = [CannotConnectError()]
    with pytest.raises(UpdateFailedError):
        await coordinator._async_update_data()
    bridge.last_update_success = False
    client.ezviz_encryption.reset_mock()
    with pytest.raises(UpdateFailedError):
        await coordinator._async_update_data()
    client.ezviz_encryption.assert_not_called()
    assert media.media_payload(None) is None
    assert media.MEDIA_INTERVAL.total_seconds() == 600


def test_microsd_entities_map_status_capacity_and_problems(monkeypatch) -> None:
    stub_modules(monkeypatch)
    media = load(monkeypatch, "ezviz_media")
    entities = load(monkeypatch, "ezviz_media_entities")
    coordinator = SimpleNamespace(
        data=media.EzvizMediaStatus(None, EzvizStorage("ok", 30436)), last_update_success=True
    )
    sensor = entities.EzvizMicroSdSensor(coordinator, ezviz_entry())
    problem = entities.EzvizMicroSdProblem(coordinator, ezviz_entry())
    assert sensor.unique_id == "ezviz-01J9ENTRY-microsd"
    assert problem.unique_id == "ezviz-01J9ENTRY-microsd-problem"
    assert sensor._attr_options == ["ok", "no_card", "unformatted", "error", "unknown"]
    assert (sensor.native_value, sensor.extra_state_attributes) == ("ok", {"capacity_mb": 30436})
    assert sensor.available and problem.is_on is False
    for status, expected in (("no_card", True), ("unformatted", True), ("error", True)):
        coordinator.data = media.EzvizMediaStatus(None, EzvizStorage(status, None))
        assert problem.is_on is expected
    coordinator.data = media.EzvizMediaStatus(None, EzvizStorage("unknown", None))
    assert problem.is_on is None
    coordinator.data = media.EzvizMediaStatus(None, None)
    assert not sensor.available and not problem.available and sensor.native_value is None
    coordinator.data = media.EzvizMediaStatus(None, EzvizStorage("ok", None))
    coordinator.last_update_success = False
    assert not sensor.available


def ws_env(monkeypatch, client):
    stub_modules(
        monkeypatch,
        voluptuous=ha_stub_support.VOLUPTUOUS_STUB,
        **{
            "homeassistant.components.http": {"HomeAssistantView": object},
            "homeassistant.components.websocket_api": {
                "websocket_command": lambda _schema: lambda handler: handler,
                "async_response": lambda handler: handler,
                "async_register_command": Mock(),
            },
        },
    )
    components = ModuleType("homeassistant.components")
    components.websocket_api = sys.modules["homeassistant.components.websocket_api"]
    monkeypatch.setitem(sys.modules, components.__name__, components)
    util = ModuleType("homeassistant.util")
    util.dt = sys.modules["homeassistant.util.dt"]
    monkeypatch.setitem(sys.modules, util.__name__, util)
    load(monkeypatch, "ezviz_alarm_api")
    module = load(monkeypatch, "ezviz_media_websocket")
    entry = ezviz_entry()
    entry.runtime_data = SimpleNamespace(client=client)
    hass = SimpleNamespace(
        config_entries=SimpleNamespace(
            async_get_entry=lambda key: entry if key == entry.entry_id else None
        ),
    )
    admin = SimpleNamespace(is_active=True, is_admin=True)
    return module, hass, SimpleNamespace(user=admin, send_result=Mock(), send_error=Mock())


def test_requested_day_is_an_iso_day_in_the_bounded_window(monkeypatch) -> None:
    module, _hass, _connection = ws_env(monkeypatch, None)
    today = date(2026, 10, 4)
    assert module.requested_day("2026-10-04", today) == today
    assert module.requested_day("2026-09-27", today) == date(2026, 9, 27)
    assert module.requested_day("2026-10-05", today) == date(2026, 10, 5)
    for value in ("2026-09-26", "2026-10-06", "2026-02-30", "04-10-2026", "2026-1-04", 20261004):
        assert module.requested_day(value, today) is None


async def test_sd_record_command_validates_and_hides_old_apps(monkeypatch) -> None:
    client = SimpleNamespace(
        ezviz_camera_identity=AsyncMock(return_value=SOURCE),
        ezviz_sd_records=AsyncMock(
            side_effect=[
                (EzvizSdRecord(10, 20, "event"),),
                EzvizFeatureUnsupportedError(),
                CannotConnectError(),
            ]
        ),
    )
    module, hass, connection = ws_env(monkeypatch, client)
    message = {"id": 1, "entry_id": "01J9ENTRY", "date": "2026-10-03"}
    await module.ws_list_sd_records(hass, connection, message)
    assert connection.send_result.call_args.args[1] == {
        "supported": True,
        "date": "2026-10-03",
        "records": [{"start": 10, "end": 20, "type": "event"}],
    }
    client.ezviz_sd_records.assert_awaited_with("front-door", date(2026, 10, 3))
    await module.ws_list_sd_records(hass, connection, message)
    assert connection.send_result.call_args.args[1]["supported"] is False
    await module.ws_list_sd_records(hass, connection, message)
    assert connection.send_error.call_args.args[1] == "unavailable"
    await module.ws_list_sd_records(hass, connection, {**message, "date": "2026-08-01"})
    assert connection.send_error.call_args.args[1] == "invalid_format"
    await module.ws_list_sd_records(hass, connection, {**message, "entry_id": "missing"})
    assert connection.send_error.call_args.args[1] == "not_found"
    client.ezviz_camera_identity.return_value = "OTHER:1"
    await module.ws_list_sd_records(hass, connection, message)
    assert connection.send_error.call_args.args[1] == "unavailable"
    assert client.ezviz_sd_records.await_count == 3


def test_panel_metadata_references_vistoda_entities_without_io(monkeypatch) -> None:
    stub_modules(monkeypatch)
    native = ModuleType("custom_components.media_bridge.ezviz_panel_metadata")
    native.panel_metadata = lambda _hass, _entry: {"device_name": "Spioncino"}
    monkeypatch.setitem(sys.modules, native.__name__, native)
    ids = {
        ("sensor", "ezviz-01J9ENTRY-microsd"): "sensor.spioncino_scheda_microsd",
        ("sensor", "ring-entry-1-unlock-mode"): "sensor.vistoda_ring_modalita_apertura",
    }
    registry = SimpleNamespace(
        async_get_entity_id=lambda domain, _platform, key: ids.get((domain, key))
    )
    sys.modules["homeassistant.helpers.entity_registry"].async_get = lambda _hass: registry
    media = load(monkeypatch, "ezviz_media")
    module = load(monkeypatch, "panel_entry_metadata")
    status = media.EzvizMediaStatus(EzvizEncryption(False, None), EzvizStorage("ok", 512))
    runtime = SimpleNamespace(ezviz_media=SimpleNamespace(data=status))
    hass = SimpleNamespace(data={})
    unbound = bind_runtime(config_entry("ezviz", "01J9ENTRY", alias="front-door"), runtime)
    assert module.entry_metadata(hass, unbound, "ezviz") == {
        "device_name": "Spioncino",
        "control_source": "vistoda",
        "delegate_available": False,
        "microsd_entity_id": "sensor.spioncino_scheda_microsd",
        "media": {
            "encryption": {"video_encrypted": False, "key_source": None},
            "storage": {"status": "ok", "capacity_mb": 512},
        },
    }
    assert module.entry_metadata(hass, config_entry("ring"), "ring") == {
        "unlock_entity_id": "sensor.vistoda_ring_modalita_apertura"
    }
    assert module.entry_metadata(hass, config_entry("ring", "other"), "ring") == {}
    assert module.entry_metadata(hass, config_entry("blink"), "blink") == {}


def test_panel_metadata_publishes_the_scenetrove_link_only_when_set(monkeypatch) -> None:
    stub_modules(monkeypatch)
    native = ModuleType("custom_components.media_bridge.ezviz_panel_metadata")
    native.panel_metadata = lambda _hass, _entry: {}
    monkeypatch.setitem(sys.modules, native.__name__, native)
    registry = SimpleNamespace(async_get_entity_id=lambda *_args: None)
    sys.modules["homeassistant.helpers.entity_registry"].async_get = lambda _hass: registry
    module = load(monkeypatch, "panel_entry_metadata")
    entry = bind_runtime(config_entry("ezviz", "01J9ENTRY"), SimpleNamespace())
    entry.options = {"scenetrove_url": "https://st.example", "scenetrove_device": "spioncino"}
    result = module.entry_metadata(SimpleNamespace(data={}), entry, "ezviz")
    assert result["scenetrove_url"] == "https://st.example"
    assert result["scenetrove_device"] == "spioncino"
    entry.options = {"scenetrove_url": ""}
    assert "scenetrove_url" not in module.entry_metadata(SimpleNamespace(data={}), entry, "ezviz")
