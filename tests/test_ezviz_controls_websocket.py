"""EZVIZ settings and PTZ through the Vistoda EZVIZ app (standalone mode)."""

import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, Mock

from ha_stub_support import config_entry, load, stub_ha

from custom_components.media_bridge.client_ezviz_controls import (
    EzvizControlConflictError,
    EzvizControls,
    EzvizControlUnconfirmedError,
    EzvizRange,
)
from custom_components.media_bridge.errors import CannotConnectError

SOURCE = "BC1234567:1"
CONTROLS = EzvizControls(
    online=True,
    defence_enabled=False,
    alarm_schedule_enabled=True,
    detection_mode="human_shape",
    sensitivity=EzvizRange(3, 1, 6),
    switches=(("logo", True), ("privacy", False), ("zoom_assist", True)),
    ptz=True,
    battery_percent=80,
    battery_work_mode="power_saving",
    firmware_version="V5.3",
    firmware_update_available=False,
)


def env(monkeypatch, controls=CONTROLS, native=None):
    stub_ha(monkeypatch)
    modules = {
        "voluptuous": {"Required": str, "All": lambda *a: a, "Length": lambda **k: k},
        "homeassistant.components.websocket_api": {
            "websocket_command": lambda _schema: lambda handler: handler,
            "async_response": lambda handler: handler,
            "async_register_command": Mock(),
        },
    }
    for name, values in modules.items():
        module = ModuleType(name)
        module.__dict__.update(values)
        monkeypatch.setitem(sys.modules, name, module)
    sys.modules["voluptuous"].Any = lambda *a: a
    sys.modules["voluptuous"].In = lambda values: values
    components = ModuleType("homeassistant.components")
    components.websocket_api = sys.modules["homeassistant.components.websocket_api"]
    monkeypatch.setitem(sys.modules, components.__name__, components)
    status = load(monkeypatch, "ezviz_controls")
    load(monkeypatch, "ezviz_controls_settings")
    load(monkeypatch, "ezviz_controls_websocket")
    module = load(monkeypatch, "ezviz_settings_websocket")
    entry = config_entry("ezviz", "E1", alias="front-door", ezviz_source_id=SOURCE)
    data = status.UNSUPPORTED if controls is None else status.EzvizControlsStatus(True, controls)
    coordinator = SimpleNamespace(data=data, last_update_success=True)
    coordinator.async_refresh = AsyncMock()
    coordinator.async_apply = Mock()
    client = SimpleNamespace(
        ezviz_camera_identity=AsyncMock(return_value=SOURCE),
        ezviz_set_control=AsyncMock(),
        ezviz_ptz=AsyncMock(),
    )
    runtime = SimpleNamespace(client=client, ezviz_controls=coordinator)
    hass = SimpleNamespace(
        data={"media_bridge": {"E1": runtime}},
        config_entries=SimpleNamespace(
            async_get_entry=lambda key: entry if key == "E1" else None,
            async_entries=lambda _domain: [] if native is None else [native],
        ),
    )
    connection = SimpleNamespace(
        user=SimpleNamespace(is_admin=True), send_result=Mock(), send_error=Mock()
    )
    return module, hass, connection, runtime


def request(key="camera_defence", value=True, expected=False):
    return {"id": 9, "entry_id": "E1", "key": key, "value": value, "expected_value": expected}


def test_app_controls_map_to_existing_keys_and_hide_unreported_items(monkeypatch) -> None:
    env(monkeypatch)
    mapping = load(monkeypatch, "ezviz_controls_settings")
    settings = {item["key"]: item for item in mapping.settings_from_controls(CONTROLS)}
    assert list(settings) == [
        "camera_defence",
        "alarm_schedule",
        "battery_level",
        "battery_work_mode",
        "detection_mode",
        "detection_sensitivity",
        "logo_watermark",
        "privacy_mode",
        "switch.zoom_assist",
        "firmware_version",
        "firmware_update",
    ]
    assert settings["detection_sensitivity"] == {
        "key": "detection_sensitivity",
        "group": "detection",
        "kind": "number",
        "value": 3,
        "min": 1,
        "max": 6,
    }
    assert settings["switch.zoom_assist"]["group"] == "other"
    assert settings["battery_level"]["kind"] == "info"
    keys = {key: mapping.control_key(key, CONTROLS) for key in settings}
    assert keys["camera_defence"] == "defence_enabled"
    assert keys["detection_sensitivity"] == "sensitivity"
    assert keys["logo_watermark"] == "switch.logo"
    assert keys["privacy_mode"] == "switch.privacy"
    assert keys["switch.zoom_assist"] == "switch.zoom_assist"
    assert keys["alarm_schedule"] is keys["battery_level"] is keys["firmware_version"] is None
    assert mapping.control_key("wide_dynamic_range", CONTROLS) is None  # not reported
    assert mapping.settings_from_controls(EzvizControls()) == []
    assert mapping.valid_value("detection_sensitivity", 6, CONTROLS)
    assert not mapping.valid_value("detection_sensitivity", 7, CONTROLS)
    assert not mapping.valid_value("detection_sensitivity", True, CONTROLS)
    assert not mapping.valid_value("detection_mode", "vehicle", CONTROLS)
    assert not mapping.valid_value("camera_defence", 1, CONTROLS)


async def test_info_and_confirmed_write_go_through_the_app(monkeypatch) -> None:
    module, hass, connection, runtime = env(monkeypatch)
    await module.ws_settings_info(hass, connection, {"id": 1, "entry_id": "E1"})
    result = connection.send_result.call_args.args[1]
    assert result["source"] == "vistoda"
    confirmed = EzvizControls(defence_enabled=True)
    runtime.client.ezviz_set_control.return_value = confirmed
    await module.ws_settings_set(hass, connection, request())
    runtime.client.ezviz_set_control.assert_awaited_once_with(
        "front-door", "defence_enabled", True, False
    )
    runtime.ezviz_controls.async_apply.assert_called_once_with(confirmed)
    assert connection.send_result.call_args.args[1]["settings"] == [
        {"key": "camera_defence", "group": "arming", "kind": "boolean", "value": True}
    ]
    await module.ws_settings_set(hass, connection, request("detection_sensitivity", 5, 3))
    assert runtime.client.ezviz_set_control.await_args.args[1:] == ("sensitivity", 5, 3)


async def test_conflict_unconfirmed_and_errors_refresh_and_report(monkeypatch) -> None:
    module, hass, connection, runtime = env(monkeypatch)
    runtime.client.ezviz_set_control.side_effect = [
        EzvizControlConflictError(),
        EzvizControlUnconfirmedError(),
        CannotConnectError(),
    ]
    for code in ("conflict", "unconfirmed", "unavailable"):
        await module.ws_settings_set(hass, connection, request("privacy_mode", True, False))
        assert connection.send_error.call_args.args[1] == code
    assert runtime.ezviz_controls.async_refresh.await_count == 3
    runtime.ezviz_controls.async_apply.assert_not_called()


async def test_invalid_read_only_and_retargeted_requests_never_write(monkeypatch) -> None:
    module, hass, connection, runtime = env(monkeypatch)
    await module.ws_settings_set(hass, connection, request("alarm_schedule", False, True))
    assert connection.send_error.call_args.args[1] == "not_supported"
    await module.ws_settings_set(hass, connection, request("detection_sensitivity", 9, 3))
    assert connection.send_error.call_args.args[1] == "invalid_format"
    await module.ws_settings_set(hass, connection, request("receive_device_message"))
    assert connection.send_error.call_args.args[1] == "not_supported"
    runtime.client.ezviz_camera_identity.return_value = "OTHER:1"
    await module.ws_settings_set(hass, connection, request())
    assert connection.send_error.call_args.args[1] == "unavailable"
    runtime.client.ezviz_set_control.assert_not_awaited()


async def test_failing_app_is_never_replaced_by_the_native_session(monkeypatch) -> None:
    module, hass, connection, runtime = env(monkeypatch)
    runtime.ezviz_controls.last_update_success = False
    await module.ws_settings_info(hass, connection, {"id": 1, "entry_id": "E1"})
    runtime.ezviz_controls.async_refresh.assert_awaited_once()
    assert connection.send_error.call_args.args[1] == "unavailable"


async def test_older_app_never_falls_back_to_the_native_coordinator(monkeypatch) -> None:
    native = SimpleNamespace(data={"BC1234567": {"alarm_notify": True}}, last_update_success=True)
    module, hass, connection, runtime = env(
        monkeypatch, controls=None, native=SimpleNamespace(runtime_data=native)
    )
    await module.ws_settings_info(hass, connection, {"id": 1, "entry_id": "E1"})
    assert connection.send_error.call_args.args[1] == "app_outdated"
    connection.send_result.assert_not_called()
    runtime.client.ezviz_set_control.assert_not_awaited()


async def test_ptz_uses_the_app_only_when_it_reports_ptz(monkeypatch) -> None:
    _module, hass, connection, runtime = env(monkeypatch)
    ptz = sys.modules["custom_components.media_bridge.ezviz_controls_websocket"].ws_ptz
    message = {"id": 3, "entry_id": "E1", "direction": "up"}
    await ptz(hass, connection, message)
    runtime.client.ezviz_ptz.assert_awaited_once_with("front-door", "up")
    assert connection.send_result.call_args.args[1] == {"direction": "up"}
    runtime.client.ezviz_ptz.side_effect = [EzvizControlConflictError(), CannotConnectError()]
    await ptz(hass, connection, message)
    assert connection.send_error.call_args.args[1] == "not_supported"
    await ptz(hass, connection, message)
    assert connection.send_error.call_args.args[1] == "unavailable"
    _module, hass, connection, runtime = env(monkeypatch, controls=EzvizControls(ptz=False))
    await sys.modules["custom_components.media_bridge.ezviz_controls_websocket"].ws_ptz(
        hass, connection, message
    )
    assert connection.send_error.call_args.args[1] == "not_supported"
    runtime.client.ezviz_ptz.assert_not_awaited()
