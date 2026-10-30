"""Event archive layout, idempotence, listing, pictures and retention on a fake mount."""

import json
import os
import sys

import pytest
from release_flow_support import framework

JPEG = b"\xff\xd8\xff\xe0jpeg\xff\xd9"


def archive(monkeypatch):
    module = framework(monkeypatch).load("event_archive")
    storage = sys.modules["custom_components.media_bridge.backup_storage"]
    monkeypatch.setattr(storage, "network_filesystem", lambda path: "nfs")
    return module


def alarm(alarm_id, occurred_at, category="person"):
    return {
        "alarm_id": alarm_id,
        "occurred_at": occurred_at,
        "category": category,
        "alarm_type": 10000,
        "title": "Persona rilevata",
    }


# 2026-10-28T19:00:00Z and the next days.
DAY = 1_793_214_000


def test_event_ids_sort_by_time_and_reject_unsafe_ids(monkeypatch):
    module = archive(monkeypatch)
    assert module.event_id(DAY, "evt-1") == "20261028T190000Z-evt-1"
    for bad in ("", "../x", "a/b", "x" * 97):
        with pytest.raises(ValueError):
            module.event_id(DAY, bad)


def test_write_event_is_idempotent(monkeypatch, tmp_path):
    module = archive(monkeypatch)
    assert module.write_event(tmp_path, "ezviz", "front-door", alarm("evt-1", DAY), JPEG)
    assert not module.write_event(tmp_path, "ezviz", "front-door", alarm("evt-1", DAY), JPEG)
    folder = tmp_path / "events" / "ezviz" / "front-door" / "2026" / "10"
    assert sorted(path.name for path in folder.iterdir()) == [
        "20261028T190000Z-evt-1.jpg",
        "20261028T190000Z-evt-1.json",
    ]
    stored = json.loads((folder / "20261028T190000Z-evt-1.json").read_text())
    assert stored["schema_version"] == 1
    assert stored["picture"] == "20261028T190000Z-evt-1.jpg"
    assert set(stored) == {
        "schema_version", "provider", "camera", "alarm_id", "occurred_at",
        "category", "alarm_type", "title", "picture", "archived_at",
    }  # fmt: skip
    assert not list(folder.glob(".*partial"))


def test_listing_pages_newest_first_and_filters_by_day(monkeypatch, tmp_path):
    module = archive(monkeypatch)
    for number in range(12):
        module.write_event(
            tmp_path, "ezviz", "front-door", alarm(f"e{number}", DAY + number * 3600), None
        )
    first = module.list_events(tmp_path, "ezviz", "front-door", 1, 5)
    assert [item["alarm_id"] for item in first["items"]] == ["e11", "e10", "e9", "e8", "e7"]
    assert first["pagination"]["total_items"] == 12
    assert first["pagination"]["total_pages"] == 3
    assert first["items"][0]["picture"] is False
    same_day = module.list_events(tmp_path, "ezviz", "front-door", 1, 50, day="2026-10-28")
    assert [item["alarm_id"] for item in same_day["items"]] == ["e4", "e3", "e2", "e1", "e0"]


def test_listing_skips_unsafe_and_foreign_files(monkeypatch, tmp_path):
    module = archive(monkeypatch)
    module.write_event(tmp_path, "ezviz", "front-door", alarm("good", DAY), None)
    folder = tmp_path / "events" / "ezviz" / "front-door" / "2026" / "10"
    good = json.loads((folder / "20261028T190000Z-good.json").read_text())
    (folder / "20261028T190001Z-v2.json").write_text(json.dumps({**good, "schema_version": 2}))
    (folder / "20261028T190002Z-big.json").write_text(" " * 20000)
    (folder / "20261028T190003Z-other.json").write_text(json.dumps({**good, "provider": "blink"}))
    (folder / "20261028T190004Z-mismatch.json").write_text(json.dumps(good))
    outside = tmp_path / "outside"
    outside.mkdir()
    os.symlink(outside, tmp_path / "events" / "ezviz" / "front-door" / "2025")
    listed = module.list_events(tmp_path, "ezviz", "front-door", 1, 50)
    assert [item["alarm_id"] for item in listed["items"]] == ["good"]


def test_pictures_are_checked_paths(monkeypatch, tmp_path):
    module = archive(monkeypatch)
    module.write_event(tmp_path, "ezviz", "front-door", alarm("evt-1", DAY), JPEG)
    path = module.event_picture(tmp_path, "ezviz", "front-door", "20261028T190000Z-evt-1")
    assert path.read_bytes() == JPEG
    for bad in ("../../x", "20261028T190000Z-missing", "nope"):
        with pytest.raises(ValueError):
            module.event_picture(tmp_path, "ezviz", "front-door", bad)


def test_prune_removes_only_old_events(monkeypatch, tmp_path):
    module = archive(monkeypatch)
    module.write_event(tmp_path, "ezviz", "front-door", alarm("old", DAY), JPEG)
    module.write_event(tmp_path, "ezviz", "front-door", alarm("new", DAY + 86400 * 30), JPEG)
    assert module.prune_events(tmp_path, "ezviz", "front-door", older_than=DAY + 86400) == 1
    listed = module.list_events(tmp_path, "ezviz", "front-door", 1, 50)
    assert [item["alarm_id"] for item in listed["items"]] == ["new"]
    assert not list((tmp_path / "events").rglob("*-old.jpg"))


def test_absent_mount_is_an_error(monkeypatch, tmp_path):
    module = archive(monkeypatch)
    storage = sys.modules["custom_components.media_bridge.backup_storage"]
    monkeypatch.setattr(storage, "network_filesystem", lambda path: None)
    with pytest.raises(OSError):
        module.write_event(tmp_path, "ezviz", "front-door", alarm("evt-1", DAY), None)
    with pytest.raises(ValueError):
        module.list_events(tmp_path, "ezviz", "front-door", 1, 10)


def test_has_event_and_other_writers_partials(monkeypatch, tmp_path):
    module = archive(monkeypatch)
    folder = tmp_path / "events" / "ezviz" / "front-door" / "2026" / "10"
    folder.mkdir(parents=True)
    other = folder / ".20261028T190000Z-evt-1.json.partial"
    other.write_bytes(b"another writer")
    assert not module.has_event(tmp_path, "ezviz", "front-door", DAY, "evt-1")
    module.write_event(tmp_path, "ezviz", "front-door", alarm("evt-1", DAY), JPEG)
    assert module.has_event(tmp_path, "ezviz", "front-door", DAY, "evt-1")
    assert other.read_bytes() == b"another writer", "temporary files are private to a writer"


def test_a_page_reads_only_its_own_records(monkeypatch, tmp_path):
    module = archive(monkeypatch)
    for number in range(30):
        module.write_event(
            tmp_path, "ezviz", "front-door", alarm(f"e{number}", DAY + number * 60), None
        )
    reads = []
    original = module._read
    monkeypatch.setattr(module, "_read", lambda *args: reads.append(1) or original(*args))
    page = module.list_events(tmp_path, "ezviz", "front-door", 2, 5)
    assert [item["alarm_id"] for item in page["items"]] == ["e24", "e23", "e22", "e21", "e20"]
    assert page["pagination"]["total_items"] == 30
    assert len(reads) == 5
