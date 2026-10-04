"""Optional Ring 0.16 unlock settings: tolerant parsing and a read-only sensor."""

import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock

import pytest
from ha_stub_support import Entity, config_entry, load, stub_ha

from custom_components.media_bridge.errors import CannotConnectError
from custom_components.media_bridge.models import parse_ring_status
from custom_components.media_bridge.ring_unlock import (
    RingUnlockSettings,
    parse_unlock_settings,
    unlock_mode_unique_id,
)

BASE = {
    "battery": 80,
    "online": True,
    "doorbell_volume": 4,
    "mic_volume": 5,
    "voice_volume": 6,
    "last_activity": None,
    "device_id": "42",
}


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        ("direct", None),
        ({}, None),
        ({"mode": "direct", "duration_seconds": 5}, RingUnlockSettings("direct", None, 5)),
        (
            {"mode": "ring_to_open", "ring_to_open_enabled": True},
            RingUnlockSettings("ring_to_open", True, None),
        ),
        ({"mode": "keypad_v2"}, RingUnlockSettings("keypad_v2", None, None)),
        ({"mode": "<b>", "duration_seconds": 5}, RingUnlockSettings(None, None, 5)),
        ({"mode": "direct", "duration_seconds": True}, RingUnlockSettings("direct", None, None)),
        ({"mode": "direct", "duration_seconds": 99999}, RingUnlockSettings("direct", None, None)),
        ({"ring_to_open_enabled": "yes", "duration_seconds": -1}, None),
    ],
)
def test_unlock_settings_tolerate_missing_and_unknown_values(value, expected) -> None:
    assert parse_unlock_settings(value) == expected


def test_effective_mode_falls_back_to_the_ring_to_open_flag() -> None:
    assert RingUnlockSettings(None, True, None).effective_mode == "ring_to_open"
    assert RingUnlockSettings(None, False, 5).effective_mode is None
    assert RingUnlockSettings("direct", True, None).effective_mode == "direct"


def test_status_parsing_stays_backward_compatible() -> None:
    assert parse_ring_status(BASE).unlock_settings is None
    status = parse_ring_status({**BASE, "unlock_settings": {"mode": "direct"}})
    assert status.unlock_settings == RingUnlockSettings("direct", None, None)
    # A malformed optional block never invalidates the mandatory status.
    assert parse_ring_status({**BASE, "unlock_settings": ["x"]}).unlock_settings is None
    with pytest.raises(CannotConnectError):
        parse_ring_status({**BASE, "online": "yes", "unlock_settings": {"mode": "direct"}})


def sensor_module(monkeypatch):
    stub_ha(monkeypatch)
    sensor = ModuleType("homeassistant.components.sensor")
    sensor.SensorEntity = Entity
    monkeypatch.setitem(sys.modules, sensor.__name__, sensor)
    return load(monkeypatch, "ring_unlock_sensor")


def test_unlock_sensor_reports_mode_duration_and_device_binding(monkeypatch) -> None:
    module = sensor_module(monkeypatch)
    entry = config_entry(ring_device_id="42")
    status = parse_ring_status(
        {**BASE, "unlock_settings": {"mode": "ring_to_open", "duration_seconds": 3}}
    )
    coordinator = SimpleNamespace(data=status, last_update_success=True)
    sensor = module.RingUnlockModeSensor(coordinator, entry)
    assert sensor.unique_id == unlock_mode_unique_id(entry) == "ring-entry-1-unlock-mode"
    assert sensor._attr_translation_key == "ring_unlock_mode"
    assert sensor._attr_entity_category == "diagnostic"
    assert sensor.available and sensor.native_value == "ring_to_open"
    assert sensor.extra_state_attributes == {"ring_to_open_enabled": None, "duration_seconds": 3}
    assert module.reports_unlock_settings(status)
    coordinator.data = parse_ring_status({**BASE, "device_id": "99"})
    assert not sensor.available and sensor.native_value is None
    assert not module.reports_unlock_settings(coordinator.data)


def test_entities_are_added_only_once_the_feature_is_reported(monkeypatch) -> None:
    stub_ha(monkeypatch)
    gate = load(monkeypatch, "entity_gate")
    listeners, removed, added = [], Mock(), []
    coordinator = SimpleNamespace(data=None)
    coordinator.async_add_listener = lambda listener: listeners.append(listener) or removed
    unloads = []
    entry = SimpleNamespace(async_on_unload=unloads.append)
    gate.async_add_when_supported(entry, coordinator, bool, lambda: ["entity"], added.append)
    assert added == [] and len(listeners) == 1
    listeners[0]()
    assert added == [] and not removed.called
    coordinator.data = "supported"
    listeners[0]()
    listeners[0]()
    assert added == [["entity"]] and removed.call_count == 1
    unloads[0]()
    assert removed.call_count == 1
    gate.async_add_when_supported(entry, coordinator, bool, lambda: ["now"], added.append)
    assert added[-1] == ["now"] and len(listeners) == 1


def test_panel_sees_the_unlock_sensor_and_the_sd_record_command() -> None:
    from pathlib import Path

    component = Path("custom_components/media_bridge")
    websocket = (component / "websocket.py").read_text(encoding="utf-8")
    assert 'controls["unlock_mode"] = entity.entity_id' in websocket
    assert "async_register_ezviz_media(hass)" in websocket
    controls = (component / "frontend" / "ring-controls.js").read_text(encoding="utf-8")
    assert 'ringUnlockView(this._state("unlock_mode"))' in controls
