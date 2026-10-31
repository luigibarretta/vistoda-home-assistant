"""Every EZVIZ/Blink websocket command enforces the same access rules as its siblings."""

import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, Mock

from ha_stub_support import VOLUPTUOUS_STUB, config_entry, load, stub_ha

from tests.test_ezviz_controls_websocket import env as controls_env
from tests.test_ezviz_media_runtime import ws_env

USER = SimpleNamespace(is_active=True, is_admin=False)


async def test_ptz_needs_an_administrator(monkeypatch) -> None:
    _module, hass, connection, runtime = controls_env(monkeypatch)
    connection.user = USER
    ptz = sys.modules["custom_components.media_bridge.ezviz_controls_websocket"].ws_ptz
    await ptz(hass, connection, {"id": 3, "entry_id": "E1", "direction": "up"})
    assert connection.send_error.call_args.args[1] == "unauthorized"
    runtime.client.ezviz_ptz.assert_not_awaited()


async def test_settings_info_needs_camera_access(monkeypatch) -> None:
    module, hass, connection, runtime = controls_env(monkeypatch)
    connection.user = USER
    monkeypatch.setattr(module, "can_access_ezviz_entry", lambda *_args: False)
    await module.ws_settings_info(hass, connection, {"id": 4, "entry_id": "E1"})
    assert connection.send_error.call_args.args[1] == "unauthorized"
    runtime.ezviz_controls.async_refresh.assert_not_awaited()


async def test_sd_records_need_camera_access(monkeypatch) -> None:
    client = SimpleNamespace(ezviz_sd_records=AsyncMock(), ezviz_camera_identity=AsyncMock())
    module, hass, connection = ws_env(monkeypatch, client)
    connection.user = USER
    monkeypatch.setattr(module, "can_access_ezviz_entry", lambda *_args: False)
    await module.ws_list_sd_records(
        hass, connection, {"id": 5, "entry_id": "01J9ENTRY", "date": "2026-10-04"}
    )
    assert connection.send_error.call_args.args[1] == "unauthorized"
    client.ezviz_sd_records.assert_not_awaited()


def lists_env(monkeypatch, provider, *, access=True):
    stub_ha(monkeypatch)
    stubs = {
        "voluptuous": {**VOLUPTUOUS_STUB, "Match": lambda pattern: pattern, "In": lambda v: v},
        "homeassistant.helpers.storage": {"Store": object},
        "homeassistant.components.websocket_api": {
            "websocket_command": lambda _schema: lambda handler: handler,
            "async_response": lambda handler: handler,
            "async_register_command": Mock(),
        },
    }
    for name, values in stubs.items():
        module = ModuleType(name)
        module.__dict__.update(values)
        monkeypatch.setitem(sys.modules, name, module)
    components = ModuleType("homeassistant.components")
    components.websocket_api = sys.modules["homeassistant.components.websocket_api"]
    monkeypatch.setitem(sys.modules, components.__name__, components)
    module = load(monkeypatch, "provider_recording_list_websocket")
    entry = config_entry(provider, "E1", alias="front-door")
    hass = SimpleNamespace(
        config_entries=SimpleNamespace(async_get_entry=lambda key: entry if key == "E1" else None)
    )
    store = SimpleNamespace(
        async_snapshot=AsyncMock(return_value=[]), async_create=AsyncMock(return_value=([], "L1"))
    )
    monkeypatch.setattr(module, "async_get_provider_recording_lists", lambda _hass: store)
    monkeypatch.setattr(module, "can_access_ezviz_entry", lambda _h, _u, _e, action="read": access)
    connection = SimpleNamespace(user=USER, send_result=Mock(), send_error=Mock())
    return module, hass, connection, store


async def test_ezviz_lists_need_camera_access(monkeypatch) -> None:
    module, hass, connection, store = lists_env(monkeypatch, "ezviz", access=False)
    for handler, extra in ((module.ws_list, {}), (module.ws_create, {"name": "Ingresso"})):
        await handler(hass, connection, {"id": 6, "entry_id": "E1", "provider": "ezviz", **extra})
        assert connection.send_error.call_args.args[1] == "unauthorized"
    store.async_snapshot.assert_not_awaited()
    store.async_create.assert_not_awaited()


async def test_blink_list_changes_need_an_administrator(monkeypatch) -> None:
    module, hass, connection, store = lists_env(monkeypatch, "blink")
    await module.ws_list(hass, connection, {"id": 7, "entry_id": "E1", "provider": "blink"})
    assert connection.send_result.call_args.args[1] == {"lists": []}
    await module.ws_create(
        hass, connection, {"id": 8, "entry_id": "E1", "provider": "blink", "name": "X"}
    )
    assert connection.send_error.call_args.args[1] == "unauthorized"
    store.async_create.assert_not_awaited()


async def test_ezviz_recording_writes_need_an_administrator(monkeypatch) -> None:
    lists_env(monkeypatch, "ezviz")
    module = load(monkeypatch, "provider_recording_websocket")
    client = SimpleNamespace(
        create_provider_recording=AsyncMock(),
        create_provider_sd_recording=AsyncMock(),
        delete_provider_recording=AsyncMock(),
    )
    entry = config_entry("ezviz", "E1", alias="front-door")
    entry.runtime_data = SimpleNamespace(client=client)
    hass = SimpleNamespace(
        data={"media_bridge": {}},
        config_entries=SimpleNamespace(async_get_entry=lambda key: entry if key == "E1" else None),
    )
    connection = SimpleNamespace(user=USER, send_result=Mock(), send_error=Mock())
    messages = (
        (module.ws_create_recording, {"duration": 30}),
        (module.ws_create_sd_recording, {"start": 1, "end": 60}),
        (module.ws_delete_recording, {"recording_id": "00000000-0000-4000-8000-000000000001"}),
    )
    for handler, extra in messages:
        connection.send_error.reset_mock()
        await handler(hass, connection, {"id": 9, "entry_id": "E1", "request_id": "r", **extra})
        assert connection.send_error.call_args.args[1] == "unauthorized", handler.__name__
    for method in vars(client).values():
        method.assert_not_awaited()
