"""EZVIZ event archiver: live alarms, backfill pages, mount outages and retention."""

import logging
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from ha_stub_support import config_entry, load, stub_ha

from custom_components.media_bridge.client_ezviz_alarms import EzvizAlarmBatch, parse_alarm
from custom_components.media_bridge.errors import CannotConnectError
from tests.test_ezviz_alarm_client import item

JPEG = b"\xff\xd8\xff\xe0jpeg\xff\xd9"


def batch(sequences, older=None):
    events = tuple(parse_alarm(item(sequence)) for sequence in sequences)
    return EzvizAlarmBatch(events, max(sequences, default=0), "gen-a", older)


def archiver_env(monkeypatch, *, options=None, written=None, picture=JPEG):
    stub_ha(monkeypatch)
    event = sys.modules["homeassistant.helpers.event"]
    monkeypatch.setattr(event, "async_track_time_interval", Mock(), raising=False)
    module = load(monkeypatch, "ezviz_event_archiver")
    archive = {} if written is None else written

    def write_event(_mount, provider, camera, alarm, jpeg):
        key = (provider, camera, alarm["alarm_id"])
        if key in archive:
            return False
        archive[key] = jpeg
        return True

    monkeypatch.setattr(module, "write_event", write_event)
    monkeypatch.setattr(module, "prune_events", Mock(return_value=2))
    monkeypatch.setattr(module, "configured_mount", lambda _entry: "/media/vistoda_archives")

    async def executor(function, *args):
        return function(*args)

    hass = SimpleNamespace(async_add_executor_job=executor)
    entry = config_entry(provider="ezviz", entry_id="01J9ENTRY", alias="front-door")
    entry.options = {"event_archive": True, **(options or {})}
    client = SimpleNamespace(
        ezviz_alarms=AsyncMock(), ezviz_alarm_picture=AsyncMock(return_value=picture)
    )
    archiver = module.EzvizEventArchiver(hass, entry, client, "front-door")
    return SimpleNamespace(module=module, archiver=archiver, client=client, archive=archive)


def live(alarm_id, picture="/api/media_bridge/ezviz/01J9ENTRY/alarms/x.jpg"):
    return {
        "alarm_id": alarm_id,
        "occurred_at": 1_790_000_000,
        "category": "person",
        "alarm_type": 10000,
        "title": "Persona",
        "picture": picture,
    }


async def test_live_alarm_is_archived_with_its_picture(monkeypatch) -> None:
    env = archiver_env(monkeypatch)
    await env.archiver.archive(live("alarm-9"))
    await env.archiver.archive(live("alarm-10", picture=None))
    assert env.archive == {("ezviz", "front-door", "alarm-9"): JPEG,
                           ("ezviz", "front-door", "alarm-10"): None}  # fmt: skip
    env.client.ezviz_alarm_picture.assert_awaited_once_with("front-door", "alarm-9")


async def test_disabled_archive_writes_nothing(monkeypatch) -> None:
    env = archiver_env(monkeypatch, options={"event_archive": False})
    await env.archiver.archive(live("alarm-9"))
    await env.archiver.backfill()
    assert env.archive == {}
    env.client.ezviz_alarms.assert_not_awaited()


async def test_backfill_walks_older_pages_until_known(monkeypatch) -> None:
    known = {("ezviz", "front-door", "alarm-2"): None}
    env = archiver_env(monkeypatch, written=known)
    env.client.ezviz_alarms.side_effect = [batch([4, 5], older=4), batch([2, 3], older=2)]
    await env.archiver.backfill()
    assert sorted(key[2] for key in env.archive) == ["alarm-2", "alarm-3", "alarm-4", "alarm-5"]
    assert env.client.ezviz_alarms.await_args_list[1].kwargs == {"before": 4}
    assert env.client.ezviz_alarms.await_count == 2, "stops at the first known alarm"


async def test_backfill_stops_without_older(monkeypatch) -> None:
    env = archiver_env(monkeypatch)
    env.client.ezviz_alarms.side_effect = [batch([1, 2])]
    await env.archiver.backfill()
    assert env.client.ezviz_alarms.await_count == 1
    assert len(env.archive) == 2


async def test_archiver_survives_a_missing_mount(monkeypatch, caplog) -> None:
    env = archiver_env(monkeypatch)

    def unavailable(*_args):
        raise OSError("network mount is absent")

    monkeypatch.setattr(env.module, "write_event", unavailable)
    with caplog.at_level(logging.WARNING):
        await env.archiver.archive(live("alarm-1"))
        await env.archiver.archive(live("alarm-2"))
    assert caplog.text.count("event archive is unavailable") == 1
    env.client.ezviz_alarm_picture.side_effect = CannotConnectError()
    monkeypatch.setattr(env.module, "write_event", lambda *_args: True)
    await env.archiver.archive(live("alarm-3"))
    assert env.archiver.unavailable is False


async def test_prune_runs_with_retention_only(monkeypatch) -> None:
    env = archiver_env(monkeypatch)
    await env.archiver.prune()
    env.module.prune_events.assert_not_called()
    env.archiver.entry.options["event_retention_days"] = 30
    await env.archiver.prune()
    (_mount, provider, camera), kwargs = env.module.prune_events.call_args
    assert (provider, camera) == ("ezviz", "front-door")
    assert kwargs["older_than"] > 1_790_000_000
