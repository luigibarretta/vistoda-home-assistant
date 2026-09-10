"""Resolve Ring identity from provider, Home Assistant or user overrides."""

from typing import Any

from .const import DOMAIN

FIELDS = ("device_name", "location_name", "city")
DEFAULT_SELECTION = dict.fromkeys(FIELDS, "ring")
ALLOWED_SOURCES = {
    "device_name": {"ring", "home_assistant", "custom"},
    "location_name": {"ring", "home_assistant", "custom"},
    "city": {"ring", "custom"},
}


def home_assistant_identity(hass, entry, alias: str) -> dict[str, str]:
    """Read the user-editable HA device name and instance Location name."""
    from homeassistant.helpers import device_registry as dr

    registry = dr.async_get(hass)
    device = registry.async_get_device_by_identifier((DOMAIN, f"ring:{alias}"))
    device_name = None if device is None else device.name_by_user or device.name
    return {
        "device_name": _safe_text(device_name, entry.title),
        "location_name": _safe_text(hass.config.location_name, "Home Assistant"),
        "city": "",
    }


def normalize_settings(raw: Any) -> dict[str, dict[str, str]]:
    """Sanitize persisted configuration and preserve safe defaults."""
    raw = raw if isinstance(raw, dict) else {}
    raw_selection = raw.get("selection") if isinstance(raw.get("selection"), dict) else {}
    raw_custom = raw.get("custom") if isinstance(raw.get("custom"), dict) else {}
    selection = {
        field: source
        if (source := raw_selection.get(field)) in ALLOWED_SOURCES[field]
        else DEFAULT_SELECTION[field]
        for field in FIELDS
    }
    custom = {field: _safe_text(raw_custom.get(field), "") for field in FIELDS}
    for field in FIELDS:
        if selection[field] == "custom" and not custom[field]:
            selection[field] = DEFAULT_SELECTION[field]
    return {"selection": selection, "custom": custom}


def resolve_identity(
    provider: dict[str, str], ha_identity: dict[str, str], settings: Any
) -> dict[str, str]:
    """Apply each configured source independently."""
    normalized = normalize_settings(settings)
    result = {}
    for field in FIELDS:
        source = normalized["selection"][field]
        if source == "custom":
            value = normalized["custom"][field]
        elif source == "home_assistant":
            value = ha_identity[field]
        else:
            value = provider[field]
        fallback = "" if field == "city" else provider[field]
        result[field] = _safe_text(value, fallback)
    return result


def configuration_payload(
    provider: dict[str, str], ha_identity: dict[str, str], settings: Any
) -> dict[str, Any]:
    """Expose only display values and source choices, never provider identifiers."""
    normalized = normalize_settings(settings)
    return {
        **normalized,
        "available": {"ring": provider, "home_assistant": ha_identity},
    }


def validate_update(selection: dict[str, str], custom: dict[str, str]) -> dict[str, Any]:
    """Validate an authenticated frontend update before persistence."""
    for field in FIELDS:
        if selection.get(field) not in ALLOWED_SOURCES[field]:
            raise ValueError(f"Unsupported source for {field}")
        value = custom.get(field, "")
        if not isinstance(value, str) or len(value) > 128 or not value.isprintable():
            raise ValueError(f"Invalid custom value for {field}")
        if selection[field] == "custom" and not value:
            raise ValueError(f"Custom value required for {field}")
    return normalize_settings({"selection": selection, "custom": custom})


def _safe_text(value, fallback: str) -> str:
    return (
        value
        if isinstance(value, str)
        and len(value) <= 128
        and value.isprintable()
        and (value or not fallback)
        else fallback
    )
