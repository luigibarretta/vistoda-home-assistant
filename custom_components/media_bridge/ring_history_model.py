"""Pure Ring history wording and source-deduplication helpers."""

from datetime import datetime

DEDUPE_SECONDS = 12
HISTORY_TYPES = {"unlock", "live_view", "ding", "motion", "activity"}


def unlock_message(identity: dict[str, str], local: datetime) -> str:
    """Render the stable user-requested notification sentence."""
    city = identity.get("city", "")
    location = identity["location_name"]
    city_suffix = "" if _already_contains_city(location, city) else f" in {city}" if city else ""
    return (
        f"Your {identity['device_name']} in {location}{city_suffix} was used to "
        f"unlock the entrance on {local:%d/%m/%Y} at {local:%H:%M}"
    )


def _already_contains_city(location: str, city: str) -> bool:
    """Recognize Ring's combined ``Home in City`` Location label."""
    return bool(city) and location.casefold().endswith(f" in {city}".casefold())


def sources_overlap(left: str, right: str) -> bool:
    """Identify different delivery paths for the same physical event."""
    left_parts = left.split(":", 2)
    right_parts = right.split(":", 2)
    left_kind = left_parts[0]
    right_kind = right_parts[0]
    left_channel = left_parts[1] if len(left_parts) > 1 else ""
    right_channel = right_parts[1] if len(right_parts) > 1 else ""
    return left != right and (
        {left_kind, right_kind} == {"command", "observed"}
        or (left_kind == right_kind == "observed" and left_channel != right_channel)
    )


def safe_name(value, fallback: str) -> str:
    """Keep only bounded printable display names."""
    return (
        value
        if isinstance(value, str) and value and len(value) <= 128 and value.isprintable()
        else fallback
    )


def event_is_valid(item) -> bool:
    """Validate one persisted local history event."""
    return (
        isinstance(item, dict)
        and isinstance(item.get("event_id"), str)
        and 0 < len(item["event_id"]) <= 128
        and item["event_id"].isprintable()
        and item.get("event_type") in HISTORY_TYPES
        and isinstance(item.get("occurred_at"), int)
        and item["occurred_at"] >= 0
    )


def same_activity(left, right) -> bool:
    """Match equivalent provider and local activities inside the dedupe window."""
    return (
        left["event_type"] == right["event_type"]
        and abs(left["occurred_at"] - right["occurred_at"]) <= DEDUPE_SECONDS
    )
