"""Archived EZVIZ event list and picture view: access, opt-in and safe names."""

import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from aiohttp import web
from ha_stub_support import load

from tests.test_ezviz_alarm_runtime import ADMIN, api_env

JPEG = b"\xff\xd8\xff\xe0jpeg\xff\xd9"
EVENT = "20261028T190000Z-evt-1"


def events_env(monkeypatch, tmp_path, *, enabled=True):
    env = api_env(monkeypatch, SimpleNamespace(ezviz_camera_identity=AsyncMock()))
    module = load(monkeypatch, "event_archive_api")
    storage = sys.modules["custom_components.media_bridge.backup_storage"]
    monkeypatch.setattr(storage, "network_filesystem", lambda path, **_: "nfs")
    monkeypatch.setattr(module, "configured_mount", lambda _entry: tmp_path)
    archive = sys.modules["custom_components.media_bridge.event_archive"]
    for alarm_id, occurred_at, jpeg in (
        ("evt-1", 1_793_214_000, JPEG),
        ("evt-2", 1_793_217_600, None),
    ):
        alarm = {"alarm_id": alarm_id, "occurred_at": occurred_at, "category": "person",
                 "alarm_type": 10000, "title": "Persona"}  # fmt: skip
        archive.write_event(tmp_path, "ezviz", "front-door", alarm, jpeg)
    entry = env.hass.config_entries.async_get_entry("01J9ENTRY")
    entry.options = {"event_archive": enabled}

    async def executor(function, *args):
        return function(*args)

    env.hass.async_add_executor_job = executor
    connection = SimpleNamespace(user=ADMIN, send_result=Mock(), send_error=Mock())
    return SimpleNamespace(module=module, env=env, connection=connection)


async def list_events(env, **extra):
    await env.module.ws_list_events(
        env.env.hass, env.connection, {"id": 1, "entry_id": "01J9ENTRY", **extra}
    )


async def test_list_requires_camera_access(monkeypatch, tmp_path) -> None:
    env = events_env(monkeypatch, tmp_path)
    monkeypatch.setattr(env.module, "can_access_ezviz_entry", lambda *_args: False)
    await list_events(env)
    assert env.connection.send_error.call_args.args[1] == "unauthorized"
    env.connection.send_result.assert_not_called()


async def test_disabled_archive_answers_enabled_false(monkeypatch, tmp_path) -> None:
    env = events_env(monkeypatch, tmp_path, enabled=False)
    await list_events(env)
    assert env.connection.send_result.call_args.args[1]["enabled"] is False


async def test_items_carry_signed_picture_paths(monkeypatch, tmp_path) -> None:
    env = events_env(monkeypatch, tmp_path)
    await list_events(env, page=1, page_size=10)
    result = env.connection.send_result.call_args.args[1]
    assert result["enabled"] is True
    assert result["pagination"]["total_items"] == 2
    assert [item["picture"] for item in result["items"]] == [
        None,
        f"/api/media_bridge/events/01J9ENTRY/{EVENT}.jpg",
    ]
    await list_events(env, day="28-10-2026")
    assert env.connection.send_error.call_args.args[1] == "invalid_format"


async def test_picture_view_rejects_unsafe_names(monkeypatch, tmp_path) -> None:
    env = events_env(monkeypatch, tmp_path)
    view = env.module.EventPictureView()
    response = await view.get(env.env.request, "01J9ENTRY", EVENT)
    assert response.headers["Cache-Control"].startswith("private")
    for name in ("../../etc/passwd", "20261028T190000Z-evt-2", "nope"):
        with pytest.raises(web.HTTPNotFound):
            await view.get(env.env.request, "01J9ENTRY", name)
    monkeypatch.setattr(env.module, "can_access_ezviz_entry", lambda *_args: False)
    with pytest.raises(web.HTTPForbidden):
        await view.get(env.env.request, "01J9ENTRY", EVENT)
