"""Ring history deduplication and notification wording contracts."""

from datetime import datetime
from zoneinfo import ZoneInfo

from custom_components.media_bridge.ring_history_model import sources_overlap, unlock_message
from custom_components.media_bridge.ring_identity import normalize_settings, resolve_identity


def test_unlock_notification_matches_requested_dynamic_sentence() -> None:
    message = unlock_message(
        {"device_name": "Front Entrance", "location_name": "Home", "city": "Casoria"},
        datetime(2026, 9, 10, 19, 30, tzinfo=ZoneInfo("Europe/Rome")),
    )
    assert message == (
        "Your Front Entrance in Home in Casoria was used to unlock the entrance "
        "on 10/09/2026 at 19:30"
    )


def test_observation_deduplicates_a_command_but_not_two_native_unlocks() -> None:
    assert sources_overlap("command:native_button", "observed:native:12")
    assert sources_overlap("observed:native:12", "observed:official")
    assert not sources_overlap("observed:native:12", "observed:native:13")
    assert not sources_overlap("command:native_button", "command:native_service")


def test_ring_identity_sources_are_independent_and_custom_values_are_bounded() -> None:
    settings = normalize_settings(
        {
            "selection": {
                "device_name": "home_assistant",
                "location_name": "custom",
                "city": "ring",
            },
            "custom": {"location_name": "Casa Barretta"},
        }
    )
    identity = resolve_identity(
        {"device_name": "Front Entrance", "location_name": "Home", "city": "Casoria"},
        {"device_name": "Citofono HA", "location_name": "Casa", "city": ""},
        settings,
    )
    assert identity == {
        "device_name": "Citofono HA",
        "location_name": "Casa Barretta",
        "city": "Casoria",
    }
