"""Persistent Ring recording-list model contracts."""

import pytest

from custom_components.media_bridge.recording_list_model import (
    RecordingListData,
    RecordingListError,
)


def test_lists_are_entry_scoped_and_membership_is_idempotent() -> None:
    model = RecordingListData(None)
    lists, list_id = model.create("ring-a", "  Da rivedere  ")
    assert lists == [{"list_id": list_id, "name": "Da rivedere", "recording_ids": []}]

    lists, changed = model.set_membership("ring-a", list_id, "recording-1", True)
    assert changed is True
    assert lists[0]["recording_ids"] == ["recording-1"]
    _, changed = model.set_membership("ring-a", list_id, "recording-1", True)
    assert changed is False
    assert model.snapshot("ring-b")[0] == []


def test_duplicate_names_are_rejected_case_insensitively() -> None:
    model = RecordingListData(None)
    model.create("ring-a", "Preferite")
    with pytest.raises(RecordingListError, match="duplicate_name"):
        model.create("ring-a", " preferite ")


def test_snapshot_prunes_orphans_and_delete_keeps_media_outside_the_model() -> None:
    model = RecordingListData(None)
    _, list_id = model.create("ring-a", "Importanti")
    model.set_membership("ring-a", list_id, "keep", True)
    model.set_membership("ring-a", list_id, "orphan", True)

    lists, changed = model.snapshot("ring-a", {"keep"})
    assert changed is True
    assert lists[0]["recording_ids"] == ["keep"]
    lists, deleted = model.delete("ring-a", list_id)
    assert deleted is True
    assert lists == []


def test_corrupt_or_duplicate_stored_values_are_sanitized() -> None:
    model = RecordingListData(
        {
            "entries": {
                "ring-a": [
                    {"list_id": "one", "name": "Lista", "recording_ids": ["a", "a", 1]},
                    {"list_id": "two", "name": " lista ", "recording_ids": ["b"]},
                    {"list_id": "", "name": "Invalid", "recording_ids": []},
                ]
            }
        }
    )
    lists, changed = model.snapshot("ring-a")
    assert changed is True
    assert lists == [{"list_id": "one", "name": "Lista", "recording_ids": ["a"]}]
