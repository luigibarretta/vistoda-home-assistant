"""Persistent Ring recording-list model contracts."""

import pytest

from custom_components.media_bridge.recording_list_model import (
    MAX_RECORDINGS_PER_LIST,
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


def test_list_can_be_renamed_without_losing_memberships() -> None:
    model = RecordingListData(None)
    _, first_id = model.create("ring-a", "Da rivedere")
    model.set_membership("ring-a", first_id, "recording-1", True)
    _, second_id = model.create("ring-a", "Importanti")

    lists, changed = model.update("ring-a", first_id, "  Preferite  ")

    assert changed is True
    assert lists[0] == {
        "list_id": first_id,
        "name": "Preferite",
        "recording_ids": ["recording-1"],
    }
    with pytest.raises(RecordingListError, match="duplicate_name"):
        model.update("ring-a", second_id, "preferite")
    with pytest.raises(RecordingListError, match="list_not_found"):
        model.update("ring-a", "missing", "Nuova")


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


def test_bulk_memberships_add_multiple_recordings_to_multiple_lists_idempotently() -> None:
    model = RecordingListData(None)
    _, first_id = model.create("blink:entry", "Eventi")
    _, second_id = model.create("blink:entry", "Da rivedere")

    lists, changed, added = model.add_memberships(
        "blink:entry", [first_id, second_id, first_id], ["local:a", "local:b", "local:a"]
    )

    assert changed is True
    assert added == 4
    assert lists[0]["recording_ids"] == ["local:a", "local:b"]
    assert lists[1]["recording_ids"] == ["local:a", "local:b"]
    _, changed, added = model.add_memberships(
        "blink:entry", [first_id, second_id], ["local:a", "local:b"]
    )
    assert changed is False
    assert added == 0


def test_bulk_memberships_fail_atomically_when_any_target_is_invalid() -> None:
    model = RecordingListData(None)
    _, list_id = model.create("ezviz:entry", "Importanti")

    with pytest.raises(RecordingListError, match="list_not_found"):
        model.add_memberships("ezviz:entry", [list_id, "missing"], ["local:a"])

    assert model.snapshot("ezviz:entry")[0][0]["recording_ids"] == []


def test_bulk_memberships_preflight_every_capacity_before_mutation() -> None:
    model = RecordingListData(None)
    _, empty_id = model.create("blink:entry", "Vuota")
    _, full_id = model.create("blink:entry", "Piena")
    model.data["entries"]["blink:entry"][1]["recording_ids"] = [
        f"usb:{value}" for value in range(MAX_RECORDINGS_PER_LIST)
    ]

    with pytest.raises(RecordingListError, match="membership_limit"):
        model.add_memberships("blink:entry", [empty_id, full_id], ["local:new"])

    lists = model.snapshot("blink:entry")[0]
    assert lists[0]["recording_ids"] == []
    assert len(lists[1]["recording_ids"]) == MAX_RECORDINGS_PER_LIST
