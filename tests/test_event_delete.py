"""Deleting archived EZVIZ events: administrators only, safe names, every folder."""

from types import SimpleNamespace
from unittest.mock import Mock

from test_event_archive_api import EVENT, events_env

OTHER = "20261028T200000Z-evt-2"


async def delete(env, ids, *, admin=True):
    env.connection.user = SimpleNamespace(is_admin=admin, id="user")
    await env.module.ws_delete_events(
        env.env.hass, env.connection, {"id": 2, "entry_id": "01J9ENTRY", "ids": ids}
    )


async def test_delete_requires_admin(monkeypatch, tmp_path) -> None:
    env = events_env(monkeypatch, tmp_path)
    monkeypatch.setattr(env.module, "event_folders", Mock(side_effect=AssertionError("no I/O")))
    await delete(env, [EVENT], admin=False)
    assert env.connection.send_error.call_args.args[1] == "unauthorized"


async def test_deleted_events_leave_every_folder(monkeypatch, tmp_path) -> None:
    env = events_env(monkeypatch, tmp_path)
    folder = tmp_path / "events" / "ezviz" / "front-door" / "2026" / "10"
    await delete(env, [EVENT, OTHER])
    assert env.connection.send_result.call_args.args[1] == {"deleted": 2, "failed": []}
    assert not any(folder.iterdir())


async def test_delete_refuses_paths_outside_the_camera(monkeypatch, tmp_path) -> None:
    env = events_env(monkeypatch, tmp_path)
    await delete(env, ["../../etc/passwd", "20261028T190000Z-missing", EVENT])
    result = env.connection.send_result.call_args.args[1]
    assert result == {"deleted": 1, "failed": ["../../etc/passwd", "20261028T190000Z-missing"]}
