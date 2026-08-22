"""Deterministic official Ring Intercom source selection."""

from datetime import UTC, datetime

from custom_components.media_bridge.ring_contract import (
    ACTIVE_RING_SOURCES,
    BATTERY,
    OPEN_DOOR,
    RingSourceCandidate,
    select_ring_source,
    timestamp_is_recent,
    timestamps_match,
)


def candidate(
    entity_id: str,
    *,
    platform: str = "ring",
    manufacturer: str = "Ring",
    model: str = "Intercom",
    translation_key: str | None = "open_door",
    original_name: str | None = "Open door",
) -> RingSourceCandidate:
    return RingSourceCandidate(
        entity_id,
        platform,
        manufacturer,
        model,
        translation_key,
        original_name,
    )


def test_active_contract_matches_the_eight_enabled_official_entities() -> None:
    assert {spec.key for spec in ACTIVE_RING_SOURCES} == {
        "open_door",
        "ding",
        "intercom_unlock",
        "doorbell_volume",
        "mic_volume",
        "voice_volume",
        "battery",
        "last_activity",
    }


def test_selection_requires_exact_ring_intercom_identity() -> None:
    expected = candidate("button.citofono_open_door")
    noise = [
        candidate("button.camera_open_door", model="Doorbell"),
        candidate("button.other_open_door", manufacturer="Other"),
        candidate("button.bridge_open_door", platform="media_bridge"),
    ]
    assert select_ring_source([*noise, expected], OPEN_DOOR) == expected.entity_id


def test_selection_fails_closed_on_missing_or_ambiguous_sources() -> None:
    assert select_ring_source([], OPEN_DOOR) is None
    first = candidate("button.first_open_door")
    second = candidate("button.second_open_door")
    assert select_ring_source([first, second], OPEN_DOOR) is None


def test_battery_falls_back_to_official_original_name() -> None:
    expected = candidate(
        "sensor.citofono_battery",
        translation_key=None,
        original_name="Battery",
    )
    wrong = candidate(
        "sensor.citofono_other",
        translation_key=None,
        original_name="Other",
    )
    assert select_ring_source([wrong, expected], BATTERY) == expected.entity_id


def test_event_restore_requires_the_same_source_transition() -> None:
    assert timestamps_match("2026-08-22T11:05:19.233+00:00", "2026-08-22T11:05:21+00:00")
    assert not timestamps_match("2026-08-22T11:05:19+00:00", "2026-08-11T10:00:00+00:00")
    assert not timestamps_match("unknown", "2026-08-22T11:05:19+00:00")


def test_event_forwarding_requires_a_recent_provider_timestamp() -> None:
    now = datetime(2026, 8, 22, 12, 0, tzinfo=UTC)
    assert timestamp_is_recent("2026-08-22T11:59:30+00:00", now)
    assert not timestamp_is_recent("2026-08-22T11:50:00+00:00", now)
    assert not timestamp_is_recent("2026-08-22T12:00:00", now)
