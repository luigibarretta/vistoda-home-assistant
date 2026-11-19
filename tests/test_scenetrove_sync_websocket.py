"""Panel commands for the SceneTrove microSD sync: who may read, who may change."""

import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock

from ha_stub_support import config_entry, load, stub_ha

TOKEN = "scenetrove_pat_" + "a" * 43
SYNC = {"enabled": True, "interval_minutes": 360}


class FakeClient:
    def __init__(self, session, url, device, token, error=None) -> None:
        self.target = (url, device, token)
        self.calls = []
        self.error = error

    async def status(self):
        self.calls.append(("status",))
        if self.error:
            raise self.error
        return SYNC

    async def set_schedule(self, enabled, interval_minutes):
        self.calls.append(("set", enabled, interval_minutes))
        if self.error:
            raise self.error
        return {"enabled": enabled, "interval_minutes": interval_minutes}


def env(monkeypatch, admin=True, linked=True, provider="ezviz", error=None):
    stub_ha(monkeypatch)
    for name, values in {
        "voluptuous": {
            "Required": str,
            "All": lambda *a: a,
            "Length": lambda **k: k,
        },
        "homeassistant.components.websocket_api": {
            "websocket_command": lambda _schema: lambda handler: handler,
            "async_response": lambda handler: handler,
            "async_register_command": Mock(),
        },
        "homeassistant.helpers.aiohttp_client": {"async_get_clientsession": lambda hass: "s"},
    }.items():
        module = ModuleType(name)
        module.__dict__.update(values)
        monkeypatch.setitem(sys.modules, name, module)
    components = ModuleType("homeassistant.components")
    components.websocket_api = sys.modules["homeassistant.components.websocket_api"]
    monkeypatch.setitem(sys.modules, components.__name__, components)
    module = load(monkeypatch, "scenetrove_sync_websocket")
    clients = []

    def make_client(*args):
        clients.append(FakeClient(*args, error=error))
        return clients[-1]

    monkeypatch.setattr(module, "SceneTroveSyncClient", make_client)
    monkeypatch.setattr(module, "can_access_ezviz_entry", lambda _h, user, _e: user.allowed)
    entry = config_entry(provider=provider, entry_id="E1")
    if linked:
        entry.options = {
            "scenetrove_url": "https://st.example",
            "scenetrove_device": "spioncino",
            "scenetrove_token": TOKEN,
        }
    hass = SimpleNamespace(
        config_entries=SimpleNamespace(async_get_entry=lambda key: entry if key == "E1" else None)
    )
    connection = SimpleNamespace(
        user=SimpleNamespace(id="u1", is_active=True, is_admin=admin, allowed=True),
        send_result=Mock(),
        send_error=Mock(),
    )
    return module, hass, connection, clients


def error(connection) -> str:
    return connection.send_error.call_args.args[1]


async def test_users_with_camera_access_read_the_schedule(monkeypatch) -> None:
    module, hass, connection, clients = env(monkeypatch, admin=False)
    await module.ws_sd_sync_info(hass, connection, {"id": 1, "entry_id": "E1"})
    assert connection.send_result.call_args.args == (1, {"sync": SYNC})
    assert clients[0].target == ("https://st.example", "spioncino", TOKEN)
    connection.user.allowed = False
    await module.ws_sd_sync_info(hass, connection, {"id": 2, "entry_id": "E1"})
    assert error(connection) == "unauthorized"


async def test_an_unlinked_entry_answers_no_sync_without_calling_scenetrove(monkeypatch) -> None:
    for kwargs in ({"linked": False}, {"provider": "blink"}):
        module, hass, connection, clients = env(monkeypatch, **kwargs)
        await module.ws_sd_sync_info(hass, connection, {"id": 1, "entry_id": "E1"})
        assert connection.send_result.call_args.args == (1, {"sync": None})
        assert clients == []


async def test_only_admins_change_it_and_only_to_offered_intervals(monkeypatch) -> None:
    module, hass, connection, clients = env(monkeypatch, admin=False)
    request = {"id": 3, "entry_id": "E1", "enabled": True, "interval_minutes": 360}
    await module.ws_sd_sync_set(hass, connection, request)
    assert error(connection) == "unauthorized"
    assert clients == []
    module, hass, connection, clients = env(monkeypatch)
    await module.ws_sd_sync_set(hass, connection, {**request, "interval_minutes": 15})
    assert error(connection) == "invalid_format"
    assert clients == []
    await module.ws_sd_sync_set(hass, connection, {**request, "enabled": False})
    assert connection.send_result.call_args.args == (
        3,
        {"sync": {"enabled": False, "interval_minutes": 360}},
    )
    assert clients[0].calls == [("set", False, 360)]


async def test_scenetrove_failures_keep_their_stable_code(monkeypatch) -> None:
    from custom_components.media_bridge.scenetrove_sync import SceneTroveSyncError

    failure = SceneTroveSyncError("scenetrove_unauthorized")
    module, hass, connection, _clients = env(monkeypatch, error=failure)
    request = {"id": 4, "entry_id": "E1", "enabled": True, "interval_minutes": 60}
    await module.ws_sd_sync_set(hass, connection, request)
    assert error(connection) == "scenetrove_unauthorized"
    connection.send_result.assert_not_called()
    module, hass, connection, _clients = env(monkeypatch, linked=False)
    await module.ws_sd_sync_set(hass, connection, request)
    assert error(connection) == "scenetrove_not_linked"
