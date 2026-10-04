"""Verified EZVIZ settings writes: read-only guard, read-back, rollback, retry cap."""

import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock

from ha_stub_support import config_entry, load, stub_ha

SERIAL = "BC1234567"


class PyEzvizError(Exception):
    pass


class FakeClient:
    """Mimics pyezvizapi 1.0.0.7, including its unbounded 504 self-retry."""

    def __init__(self, cloud, timeouts=0, sticky=False):
        self.cloud, self.timeouts, self.sticky, self.calls = cloud, timeouts, sticky, []

    def set_camera_defence(self, serial, enable, channel_no=1, max_retries=0):
        self.calls.append(("set_camera_defence", serial, enable))
        if self.timeouts:
            self.timeouts -= 1
            # Upstream passes max_retries + 1 as channel_no, so the cap never applies.
            return self.set_camera_defence(serial, enable, max_retries + 1)
        if not self.sticky:
            self.cloud["alarm_notify"] = bool(enable)
        return True


class FakeCoordinator:
    def __init__(self, client, healthy=True):
        self.ezviz_client, self.healthy = client, healthy
        self.data = {SERIAL: dict(client.cloud)}
        self.last_update_success = True

    async def async_refresh(self):
        self.last_update_success = self.healthy
        if self.healthy:
            self.data = {SERIAL: dict(self.ezviz_client.cloud)}


def env(monkeypatch, coordinator, admin=True):
    stub_ha(monkeypatch)
    modules = {
        "voluptuous": {"Required": str, "All": lambda *a: a, "Length": lambda **k: k},
        "homeassistant.components.websocket_api": {
            "websocket_command": lambda _schema: lambda handler: handler,
            "async_response": lambda handler: handler,
            "async_register_command": Mock(),
        },
        "pyezvizapi": {},
        "pyezvizapi.exceptions": {"HTTPError": PyEzvizError, "PyEzvizError": PyEzvizError},
    }
    for name, values in modules.items():
        module = ModuleType(name)
        module.__dict__.update(values)
        monkeypatch.setitem(sys.modules, name, module)
    sys.modules["voluptuous"].Any = lambda *a: a
    components = ModuleType("homeassistant.components")
    components.websocket_api = sys.modules["homeassistant.components.websocket_api"]
    monkeypatch.setitem(sys.modules, components.__name__, components)
    module = load(monkeypatch, "ezviz_settings_websocket")
    entry = config_entry(provider="ezviz", entry_id="E1", ezviz_source_id=f"{SERIAL}:1")

    async def executor(func, *args):
        return func(*args)

    hass = SimpleNamespace(
        async_add_executor_job=executor,
        config_entries=SimpleNamespace(
            async_get_entry=lambda key: entry if key == "E1" else None,
            async_entries=lambda _domain: [SimpleNamespace(runtime_data=coordinator)],
        ),
    )
    connection = SimpleNamespace(
        user=SimpleNamespace(is_admin=admin), send_result=Mock(), send_error=Mock()
    )
    return module, hass, connection


def request(key="camera_defence", value=True, expected=False):
    return {"id": 7, "entry_id": "E1", "key": key, "value": value, "expected_value": expected}


async def test_arming_write_is_confirmed_by_a_fresh_poll(monkeypatch) -> None:
    client = FakeClient({"alarm_notify": False, "supportExt": {"1": "1"}})
    module, hass, connection = env(monkeypatch, FakeCoordinator(client))
    await module.ws_settings_set(hass, connection, request())
    settings = connection.send_result.call_args.args[1]["settings"]
    assert {"key": "camera_defence", "group": "arming", "kind": "boolean", "value": True} in (
        settings
    )
    assert client.calls == [("set_camera_defence", SERIAL, 1)]


async def test_read_only_stale_and_non_admin_requests_never_write(monkeypatch) -> None:
    client = FakeClient({"alarm_notify": False, "alarm_schedules_enabled": True})
    module, hass, connection = env(monkeypatch, FakeCoordinator(client))
    await module.ws_settings_set(hass, connection, request("alarm_schedule", False, True))
    assert connection.send_error.call_args.args[1] == "not_supported"
    await module.ws_settings_set(hass, connection, request(expected=True))
    assert connection.send_error.call_args.args[1] == "conflict"
    module, hass, connection = env(monkeypatch, FakeCoordinator(client), admin=False)
    await module.ws_settings_set(hass, connection, request())
    assert connection.send_error.call_args.args[1] == "unauthorized"
    assert client.calls == []


async def test_disproved_write_is_rolled_back(monkeypatch) -> None:
    client = FakeClient({"alarm_notify": False}, sticky=True)
    module, hass, connection = env(monkeypatch, FakeCoordinator(client))
    await module.ws_settings_set(hass, connection, request())
    assert connection.send_error.call_args.args[1] == "unavailable"
    assert client.calls[-1] == ("set_camera_defence", SERIAL, 0)


async def test_failed_poll_never_rolls_back_blind(monkeypatch) -> None:
    client = FakeClient({"alarm_notify": False})
    module, hass, connection = env(monkeypatch, FakeCoordinator(client, healthy=False))
    await module.ws_settings_set(hass, connection, request())
    assert connection.send_error.call_args.args[1] == "unconfirmed"
    assert client.calls == [("set_camera_defence", SERIAL, 1)]


async def test_self_retrying_defence_call_is_capped(monkeypatch) -> None:
    client = FakeClient({"alarm_notify": False}, timeouts=50)
    module, hass, connection = env(monkeypatch, FakeCoordinator(client))
    await module.ws_settings_set(hass, connection, request())
    assert connection.send_error.call_args.args[1] == "unavailable"
    assert len(client.calls) == 3  # MAX_ATTEMPTS; the rollback is skipped on error.
    assert "set_camera_defence" not in vars(client)


async def test_invalid_value_for_an_exposed_setting_is_rejected_before_any_call(monkeypatch):
    client = FakeClient({"alarm_notify": False, "Alarm_DetectHumanCar": 1})
    module, hass, connection = env(monkeypatch, FakeCoordinator(client))
    await module.ws_settings_set(
        hass, connection, request("detection_mode", "vehicle", "human_shape")
    )
    assert connection.send_error.call_args.args[1] == "invalid_format"
    await module.ws_settings_set(hass, connection, request("camera_defence", "on", False))
    assert connection.send_error.call_args.args[1] == "invalid_format"
    assert client.calls == []
