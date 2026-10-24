"""Delegated EZVIZ arming: official camera services only, confirmed by published state."""

import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock

from ha_stub_support import config_entry, load, stub_ha
from native_ezviz_support import CAMERA, SERIAL, NativeEzviz


def env(monkeypatch, native, admin=True):
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
    load(monkeypatch, "ezviz_core")
    module = load(monkeypatch, "ezviz_settings_websocket")
    monkeypatch.setattr(module, "CONFIRM_TIMEOUT", 0.01)
    entry = config_entry(provider="ezviz", entry_id="E1", ezviz_source_id=f"{SERIAL}:1")
    entry.options = {"ezviz_delegate_controls": True}  # The native path is opt-in.
    hass = SimpleNamespace(
        config_entries=SimpleNamespace(async_get_entry=lambda key: entry if key == "E1" else None)
    )
    native.install(hass)
    connection = SimpleNamespace(
        user=SimpleNamespace(is_admin=admin),
        send_result=Mock(),
        send_error=Mock(),
        context=lambda _msg: "user-context",
    )
    return module, hass, connection


def request(key="camera_defence", value=True, expected=False):
    return {"id": 7, "entry_id": "E1", "key": key, "value": value, "expected_value": expected}


def error(connection) -> str:
    return connection.send_error.call_args.args[1]


ARMED = {"key": "camera_defence", "group": "arming", "kind": "boolean", "value": True}


async def test_arming_uses_the_official_camera_service_and_is_confirmed(monkeypatch) -> None:
    native = NativeEzviz()
    module, hass, connection = env(monkeypatch, native)
    await module.ws_settings_set(hass, connection, request())
    assert connection.send_result.call_args.args[1] == {"settings": [ARMED], "source": "native"}
    assert native.calls == [
        ("camera", "enable_motion_detection", CAMERA),
        ("homeassistant", "update_entity", CAMERA),
    ]


async def test_info_reads_the_published_camera_state_only(monkeypatch) -> None:
    module, hass, connection = env(monkeypatch, NativeEzviz(defence=True))
    await module.ws_settings_info(hass, connection, {"id": 1, "entry_id": "E1"})
    assert connection.send_result.call_args.args[1] == {"settings": [ARMED], "source": "native"}
    module, hass, connection = env(monkeypatch, NativeEzviz(online=False))
    await module.ws_settings_info(hass, connection, {"id": 1, "entry_id": "E1"})
    assert connection.send_result.call_args.args[1]["settings"] == []


async def test_other_keys_stale_and_non_admin_requests_never_call_a_service(monkeypatch) -> None:
    native = NativeEzviz()
    module, hass, connection = env(monkeypatch, native)
    await module.ws_settings_set(hass, connection, request("alarm_schedule", False, True))
    assert error(connection) == "not_supported"
    await module.ws_settings_set(hass, connection, request("wide_dynamic_range", True, False))
    assert error(connection) == "not_supported"
    await module.ws_settings_set(hass, connection, request(expected=True))
    assert error(connection) == "conflict"
    await module.ws_settings_set(hass, connection, request("camera_defence", "on", False))
    assert error(connection) == "invalid_format"
    module, hass, connection = env(monkeypatch, native, admin=False)
    await module.ws_settings_set(hass, connection, request())
    assert error(connection) == "unauthorized"
    assert native.calls == []


async def test_unconfirmed_write_is_reported_and_never_undone(monkeypatch) -> None:
    native = NativeEzviz()
    native.sticky = True
    module, hass, connection = env(monkeypatch, native)
    await module.ws_settings_set(hass, connection, request())
    assert error(connection) == "unconfirmed"
    assert [call[1] for call in native.calls] == ["enable_motion_detection", "update_entity"]


async def test_rejected_service_call_is_unavailable(monkeypatch) -> None:
    native = NativeEzviz()
    native.fail = RuntimeError("camera timed out")
    module, hass, connection = env(monkeypatch, native)
    await module.ws_settings_set(hass, connection, request())
    assert error(connection) == "unavailable"
    assert native.calls == [("camera", "enable_motion_detection", CAMERA)]


async def test_offline_or_unserved_camera_is_never_written(monkeypatch) -> None:
    for native, code in (
        (NativeEzviz(online=False), "unavailable"),
        (NativeEzviz(entries=[]), "native_unavailable"),
        (NativeEzviz(camera=False), "native_unavailable"),
        (NativeEzviz(serial="OTHER"), "native_unavailable"),
    ):
        module, hass, connection = env(monkeypatch, native)
        await module.ws_settings_set(hass, connection, request())
        assert error(connection) == code
        assert native.calls == []


async def test_a_value_already_shown_is_answered_without_a_service_call(monkeypatch) -> None:
    native = NativeEzviz(defence=True)
    module, hass, connection = env(monkeypatch, native)
    await module.ws_settings_set(hass, connection, request(value=True, expected=True))
    assert connection.send_result.call_args.args[1] == {"settings": [ARMED], "source": "native"}
    assert native.calls == []


async def test_a_disabled_official_camera_entity_serves_nothing(monkeypatch) -> None:
    native = NativeEzviz()
    native.disabled_by = "user"
    module, hass, connection = env(monkeypatch, native)
    await module.ws_settings_info(hass, connection, {"id": 1, "entry_id": "E1"})
    assert error(connection) == "native_unavailable"
