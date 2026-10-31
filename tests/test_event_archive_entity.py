"""Event archive problem sensor: available only when archiving, on during an outage."""

import sys
from types import SimpleNamespace

from ha_stub_support import config_entry, load, stub_ha


def entity_env(monkeypatch, *, enabled=True, unavailable=False):
    stub_ha(monkeypatch)
    module = load(monkeypatch, "ezviz_event_archive_entity")
    entry = config_entry(provider="ezviz", entry_id="01J9ENTRY", alias="front-door")
    archiver = SimpleNamespace(enabled=enabled, unavailable=unavailable)
    entry.runtime_data = SimpleNamespace(ezviz_events=archiver)
    monkeypatch.setattr(module, "device_info", lambda _entry: {})
    monkeypatch.setattr(module, "entity_prefix", lambda _entry: "ezviz-front-door-")
    return module.EzvizEventArchiveProblem(entry), archiver


def test_problem_follows_the_archiver(monkeypatch):
    entity, archiver = entity_env(monkeypatch)
    assert (entity.available, entity.is_on) == (True, False)
    archiver.unavailable = True
    assert entity.is_on is True
    assert entity.unique_id == "ezviz-front-door-event-archive-problem"


def test_unavailable_while_archiving_is_off(monkeypatch):
    entity, _ = entity_env(monkeypatch, enabled=False)
    assert entity.available is False


async def test_archiver_signals_outage_changes(monkeypatch):
    from tests.test_ezviz_event_archiver import archiver_env, live

    env = archiver_env(monkeypatch)
    send = sys.modules["homeassistant.helpers.dispatcher"].async_dispatcher_send
    send.reset_mock()

    def unavailable(*_args):
        raise OSError("network mount is absent")

    monkeypatch.setattr(env.module, "write_event", unavailable)
    await env.archiver.archive(live("alarm-1"))
    await env.archiver.archive(live("alarm-2"))
    monkeypatch.setattr(env.module, "write_event", lambda *_args: True)
    await env.archiver.archive(live("alarm-3"))
    signals = [call.args[1] for call in send.call_args_list]
    assert signals == ["media_bridge_ezviz_event_archive_01J9ENTRY"] * 2, "one per change"
