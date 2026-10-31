"""EZVIZ control-source routing matrix: delegation x native availability x app support."""

import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from ha_stub_support import config_entry, load, stub_ha
from native_ezviz_support import SERIAL, NativeEzviz

from custom_components.media_bridge.client_ezviz_controls import EzvizControls

CONTROLS = EzvizControls(online=False, defence_enabled=False, ptz=True)


def env(monkeypatch, *, delegate: bool, native: bool, app: bool):
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
    load(monkeypatch, "ezviz_core")
    load(monkeypatch, "ezviz_controls_websocket")
    module = load(monkeypatch, "ezviz_settings_websocket")
    entry = config_entry("ezviz", "E1", alias="front-door", ezviz_source_id=f"{SERIAL}:1")
    entry.options = {"ezviz_delegate_controls": delegate}
    data = status.EzvizControlsStatus(True, CONTROLS) if app else status.UNSUPPORTED
    controls = SimpleNamespace(data=data, last_update_success=True, async_refresh=AsyncMock())
    controls.async_apply = Mock()
    client = SimpleNamespace(
        ezviz_camera_identity=AsyncMock(return_value=f"{SERIAL}:1"),
        ezviz_set_control=AsyncMock(return_value=EzvizControls(defence_enabled=True)),
        ezviz_ptz=AsyncMock(),
    )
    runtime = SimpleNamespace(client=client, ezviz_controls=controls)
    entry.runtime_data = runtime
    hass = SimpleNamespace(
        data={"media_bridge": {}},
        config_entries=SimpleNamespace(
            async_get_entry=lambda key: entry if key == "E1" else None,
            async_entries=lambda _domain: [],
        ),
    )
    hass.native = NativeEzviz(entries=None if native else [])
    hass.native.install(hass)
    connection = SimpleNamespace(
        user=SimpleNamespace(is_active=True, is_admin=True),
        send_result=Mock(),
        send_error=Mock(),
        context=lambda _msg: None,
    )
    return module, hass, connection, entry


def outcome(connection) -> str:
    """Return the answered source, or the error code."""
    if connection.send_error.call_args:
        return connection.send_error.call_args.args[1]
    return connection.send_result.call_args.args[1]["source"]


MATRIX = [
    # (delegate, native available, app supports /controls) -> settings source
    (False, True, True, "vistoda"),
    (False, False, True, "vistoda"),
    (False, True, False, "app_outdated"),  # Never silently the native session.
    (False, False, False, "app_outdated"),
    (True, True, True, "native"),
    (True, True, False, "native"),
    (True, False, True, "native_unavailable"),  # Never silently the app either.
    (True, False, False, "native_unavailable"),
]


@pytest.mark.parametrize(("delegate", "native", "app", "expected"), MATRIX)
async def test_settings_info_and_set_follow_the_chosen_source(
    monkeypatch, delegate, native, app, expected
) -> None:
    module, hass, connection, _entry = env(monkeypatch, delegate=delegate, native=native, app=app)
    await module.ws_settings_info(hass, connection, {"id": 1, "entry_id": "E1"})
    assert outcome(connection) == expected
    connection.send_result.reset_mock()
    connection.send_error.reset_mock()
    message = {"id": 2, "entry_id": "E1", "key": "camera_defence"}
    await module.ws_settings_set(
        hass, connection, {**message, "value": True, "expected_value": False}
    )
    client = hass.config_entries.async_get_entry("E1").runtime_data.client
    assert outcome(connection) == expected
    assert client.ezviz_set_control.await_count == (expected == "vistoda")
    # Only a delegated, available entry ever calls the official camera service.
    assert hass.native.defence == (expected == "native")


@pytest.mark.parametrize(("delegate", "native", "app", "expected"), MATRIX)
async def test_ptz_uses_the_app_only_in_standalone_mode(
    monkeypatch, delegate, native, app, expected
) -> None:
    _module, hass, connection, _entry = env(monkeypatch, delegate=delegate, native=native, app=app)
    ptz = sys.modules["custom_components.media_bridge.ezviz_controls_websocket"].ws_ptz
    await ptz(hass, connection, {"id": 3, "entry_id": "E1", "direction": "up"})
    client = hass.config_entries.async_get_entry("E1").runtime_data.client
    if expected == "vistoda":
        client.ezviz_ptz.assert_awaited_once_with("front-door", "up")
        return
    client.ezviz_ptz.assert_not_awaited()
    # Delegated PTZ uses the native buttons in the panel, never this app route.
    assert connection.send_error.call_args.args[1] == (
        "app_outdated" if not delegate else "not_supported"
    )


@pytest.mark.parametrize(("delegate", "native", "app", "expected"), MATRIX)
async def test_connectivity_follows_the_chosen_source(
    monkeypatch, delegate, native, app, expected
) -> None:
    _module, hass, _connection, entry = env(monkeypatch, delegate=delegate, native=native, app=app)
    platform = load(monkeypatch, "binary_sensor")
    entity = platform.EzvizCameraConnectivity(entry)
    entity.hass = hass
    await entity.async_update()
    source = entity.extra_state_attributes["source_integration"]
    assert source == ("ezviz" if delegate else "media_bridge")
    available = {"vistoda": True, "native": True}.get(expected, False)
    assert entity.available is available
    if available:
        # The app reports the camera offline, the official camera entity online.
        assert entity.is_on is delegate


def test_native_controls_need_a_loaded_official_entry_and_camera(monkeypatch) -> None:
    _module, hass, _connection, entry = env(monkeypatch, delegate=True, native=True, app=True)
    core = sys.modules["custom_components.media_bridge.ezviz_core"]
    assert core.native_controls_available(hass, entry)
    hass.native.entries[0].state = SimpleNamespace(value="setup_retry")
    assert not core.native_controls_available(hass, entry)
    hass.native.entries[0].state = SimpleNamespace(value="loaded")
    hass.native.camera = False  # An RTSP-only or partial setup registers no camera.
    hass.native.install(hass)
    assert not core.native_controls_available(hass, entry)
    entry.options = {}
    assert not core.delegated(entry)
    del entry.options
    assert not core.delegated(entry)  # Standalone is the default.
