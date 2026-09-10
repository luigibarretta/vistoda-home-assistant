"""Pure Ring history wording and source-deduplication helpers."""

from datetime import datetime


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
