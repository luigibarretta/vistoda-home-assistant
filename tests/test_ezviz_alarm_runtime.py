"""EZVIZ alarm listener, event entity, picture view and history command."""

import asyncio
import logging
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from aiohttp import web
from ha_stub_support import config_entry, load, stub_ha

from custom_components.media_bridge.client_ezviz_alarms import (
    AlarmsUnsupportedError,
    EzvizAlarmBatch,
    parse_alarm,
)
from custom_components.media_bridge.errors import CannotConnectError
from tests.test_ezviz_alarm_client import item

SOURCE = "BC1234567:1"


def batch(sequences, next_sequence, generation="gen-a") -> EzvizAlarmBatch:
    return EzvizAlarmBatch(
        tuple(parse_alarm(item(sequence)) for sequence in sequences), next_sequence, generation
    )


def ezviz_entry():
    return config_entry(
        provider="ezviz", entry_id="01J9ENTRY", alias="front-door", ezviz_source_id=SOURCE
    )


def listener_env(monkeypatch, responses):
    stub_ha(monkeypatch)
    module = load(monkeypatch, "ezviz_alarm_listener")
    sleeps = []

    async def sleep(seconds):
        sleeps.append(seconds)

    monkeypatch.setattr(module.asyncio, "sleep", sleep)
    monkeypatch.setattr(module, "camera_name", lambda _hass, _entry: "Spioncino")
    client = SimpleNamespace(
        ezviz_alarms=AsyncMock(side_effect=[*responses, asyncio.CancelledError()]),
        ezviz_camera_identity=AsyncMock(return_value=SOURCE),
    )
    hass = SimpleNamespace(bus=SimpleNamespace(async_fire=Mock()))
    listener = module.EzvizAlarmListener(hass, ezviz_entry(), client, "front-door")
    send = sys.modules["homeassistant.helpers.dispatcher"].async_dispatcher_send
    return SimpleNamespace(
        module=module, hass=hass, client=client, listener=listener, sleeps=sleeps, send=send
    )


async def test_new_alarm_fires_once_and_history_is_never_replayed(monkeypatch) -> None:
    env = listener_env(
        monkeypatch,
        [
            batch([3, 4, 5], 5),
            batch([6], 6),
            batch([6], 6),
            batch([1, 2], 2, "gen-b"),
            batch([2, 3], 3, "gen-b"),
        ],
    )
    with pytest.raises(asyncio.CancelledError):
        await env.listener._run()
    fired = env.hass.bus.async_fire.call_args_list
    assert [call.args[1]["alarm_id"] for call in fired] == ["alarm-6", "alarm-3"]
    assert fired[0].args[0] == "vistoda_ezviz_alarm"
    assert fired[0].args[1] == {
        "entry_id": "01J9ENTRY",
        "alias": "front-door",
        "camera_name": "Spioncino",
        "category": "person",
        "alarm_type": 10000,
        "title": "Persona rilevata",
        "occurred_at": 1_790_000_006,
        "alarm_id": "alarm-6",
        "picture": "/api/media_bridge/ezviz/01J9ENTRY/alarms/alarm-6.jpg",
    }
    alarms = [call.args[2] for call in env.send.call_args_list if call.args[2] is not None]
    assert alarms == [call.args[1] for call in fired]
    first_call = env.client.ezviz_alarms.call_args_list[0]
    assert first_call.args == ("front-door", None)
    # Startup and the app restart both re-verify the pinned camera identity.
    assert env.client.ezviz_camera_identity.await_count == 2
    assert env.listener.supported is True


async def test_old_app_disables_alarms_quietly_and_rechecks_rarely(monkeypatch, caplog) -> None:
    caplog.set_level(logging.INFO)
    env = listener_env(monkeypatch, [AlarmsUnsupportedError(), AlarmsUnsupportedError()])
    with pytest.raises(asyncio.CancelledError):
        await env.listener._run()
    assert env.sleeps == [env.module.UNSUPPORTED_RETRY_SECONDS] * 2
    assert env.listener.supported is False and not env.listener.connected
    assert sum("no alarm feed" in record.message for record in caplog.records) == 1
    assert not [record for record in caplog.records if record.levelname != "INFO"]
    env.hass.bus.async_fire.assert_not_called()


async def test_transient_failures_back_off_and_retarget_fails_closed(monkeypatch) -> None:
    env = listener_env(monkeypatch, [CannotConnectError(), CannotConnectError()])
    env.client.ezviz_camera_identity.side_effect = ["OTHER:1", SOURCE, SOURCE, SOURCE]
    with pytest.raises(asyncio.CancelledError):
        await env.listener._run()
    assert env.sleeps == [2, 4, 8]
    assert env.client.ezviz_alarms.await_count == 3
    env.hass.bus.async_fire.assert_not_called()


def stub_event(monkeypatch):
    class EventEntity:
        def __init__(self):
            self.triggered, self.writes = [], 0

        async def async_added_to_hass(self):
            return None

        def _trigger_event(self, event_type, attributes=None):
            self.triggered.append((event_type, attributes))

        def async_write_ha_state(self):
            self.writes = getattr(self, "writes", 0) + 1

    module = ModuleType("homeassistant.components.event")
    module.EventEntity = EventEntity
    monkeypatch.setitem(sys.modules, module.__name__, module)


async def test_event_entity_maps_one_alarm_and_tracks_support(monkeypatch) -> None:
    stub_ha(monkeypatch)
    stub_event(monkeypatch)
    module = load(monkeypatch, "ezviz_alarm_event")
    listener = SimpleNamespace(supported=None)
    entity = module.EzvizAlarmEvent(SimpleNamespace(ezviz_alarms=listener), ezviz_entry())
    entity.triggered = []
    assert entity._attr_unique_id == "ezviz-01J9ENTRY-alarm"
    assert entity._attr_translation_key == "ezviz_alarm"
    assert entity._attr_event_types[0] == "motion" and "doorbell" in entity._attr_event_types
    assert entity.available and await entity.async_get_last_state() is None
    data = {"category": "doorbell", "alarm_id": "a1", "alarm_type": 3, "title": "Ding"}
    entity.handle_alarm({**data, "occurred_at": 9, "picture": None, "camera_name": "x"})
    assert entity.triggered == [
        (
            "doorbell",
            {"alarm_id": "a1", "alarm_type": 3, "title": "Ding", "occurred_at": 9, "picture": None},
        )
    ]
    listener.supported = False
    entity.handle_alarm(None)
    assert not entity.available and len(entity.triggered) == 1 and entity.writes == 2


def api_env(monkeypatch, runtime_client):
    stub_ha(monkeypatch)
    for name, values in {
        "voluptuous": {"Required": str, "All": lambda *a: a, "Length": lambda **k: k},
        "homeassistant.components.http": {"HomeAssistantView": object},
        "homeassistant.components.websocket_api": {
            "websocket_command": lambda _schema: lambda handler: handler,
            "async_response": lambda handler: handler,
            "async_register_command": Mock(),
        },
    }.items():
        module = ModuleType(name)
        module.__dict__.update(values)
        monkeypatch.setitem(sys.modules, name, module)
    components = ModuleType("homeassistant.components")
    components.websocket_api = sys.modules["homeassistant.components.websocket_api"]
    monkeypatch.setitem(sys.modules, components.__name__, components)
    api = load(monkeypatch, "ezviz_alarm_api")
    entry = ezviz_entry()
    runtime = SimpleNamespace(client=runtime_client, ezviz_alarms=SimpleNamespace(supported=True))
    hass = SimpleNamespace(
        data={"media_bridge": {entry.entry_id: runtime}},
        config_entries=SimpleNamespace(
            async_get_entry=lambda key: entry if key == entry.entry_id else None
        ),
    )
    return SimpleNamespace(
        api=api, hass=hass, runtime=runtime, request=SimpleNamespace(app={"hass": hass})
    )


async def test_picture_view_validates_ids_and_marks_cache_private(monkeypatch) -> None:
    jpeg = b"\xff\xd8\xff" + b"0" * 16
    client = SimpleNamespace(
        ezviz_camera_identity=AsyncMock(return_value=SOURCE),
        ezviz_alarm_picture=AsyncMock(side_effect=[jpeg, None]),
    )
    env = api_env(monkeypatch, client)
    view = env.api.EzvizAlarmPictureView()
    assert view.requires_auth is True
    assert view.url == "/api/media_bridge/ezviz/{entry_id}/alarms/{alarm_id}.jpg"
    for entry_id, alarm_id in (
        ("01J9ENTRY", "../x"),
        ("01J9ENTRY", "a.b"),
        ("../01J9", "a1"),
        ("OTHER", "a1"),
    ):
        with pytest.raises(web.HTTPNotFound):
            await view.get(env.request, entry_id, alarm_id)
    client.ezviz_alarm_picture.assert_not_called()
    result = await view.get(env.request, "01J9ENTRY", "alarm-1")
    assert result.body == jpeg and result.content_type == "image/jpeg"
    assert result.headers["Cache-Control"].startswith("private")
    client.ezviz_alarm_picture.assert_awaited_with("front-door", "alarm-1")
    with pytest.raises(web.HTTPNotFound):
        await view.get(env.request, "01J9ENTRY", "alarm-2")


async def test_history_command_reports_old_apps_without_errors(monkeypatch) -> None:
    client = SimpleNamespace(
        ezviz_camera_identity=AsyncMock(return_value=SOURCE),
        ezviz_alarms=AsyncMock(side_effect=[batch([4, 5], 5), AlarmsUnsupportedError()]),
    )
    env = api_env(monkeypatch, client)
    connection = SimpleNamespace(send_result=Mock(), send_error=Mock())
    await env.api.ws_list_alarms(env.hass, connection, {"id": 1, "entry_id": "01J9ENTRY"})
    result = connection.send_result.call_args.args[1]
    assert result["supported"] is True
    assert [alarm["alarm_id"] for alarm in result["alarms"]] == ["alarm-5", "alarm-4"]
    assert result["alarms"][0]["picture"] == "/api/media_bridge/ezviz/01J9ENTRY/alarms/alarm-5.jpg"
    client.ezviz_alarms.assert_awaited_with("front-door")
    await env.api.ws_list_alarms(env.hass, connection, {"id": 2, "entry_id": "01J9ENTRY"})
    assert connection.send_result.call_args.args[1] == {"supported": False, "alarms": []}
    client.ezviz_alarms.side_effect = [CannotConnectError()]
    await env.api.ws_list_alarms(env.hass, connection, {"id": 3, "entry_id": "01J9ENTRY"})
    assert connection.send_error.call_args.args[1] == "unavailable"
    await env.api.ws_list_alarms(env.hass, connection, {"id": 4, "entry_id": "missing"})
    assert connection.send_error.call_args.args[1] == "not_found"
