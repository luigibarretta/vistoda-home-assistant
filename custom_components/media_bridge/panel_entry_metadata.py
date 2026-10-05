"""Vistoda-owned entity references and cached media status for panel entries."""

from homeassistant.helpers import entity_registry as er

from .const import DOMAIN, PROVIDER_EZVIZ, PROVIDER_RING
from .ezviz_account import account_owner_id, defence_unique_id, reports_defence
from .ezviz_controls import BATTERY_SUFFIX, controls_payload
from .ezviz_identity import entity_prefix as ezviz_prefix
from .ezviz_media import MICROSD_PROBLEM_SUFFIX, MICROSD_SUFFIX, media_payload
from .ezviz_panel_metadata import panel_metadata
from .ring_unlock import unlock_mode_unique_id


def entry_metadata(hass, entry, provider: str) -> dict:
    """Never performs I/O: registry lookups and the last coordinator poll only."""
    registry = er.async_get(hass)
    if provider == PROVIDER_RING:
        entity_id = registry.async_get_entity_id("sensor", DOMAIN, unlock_mode_unique_id(entry))
        return {"unlock_entity_id": entity_id} if entity_id else {}
    if provider != PROVIDER_EZVIZ:
        return {}
    result = panel_metadata(hass, entry)
    for key, domain, suffix in (
        ("microsd_entity_id", "sensor", MICROSD_SUFFIX),
        ("microsd_problem_entity_id", "binary_sensor", MICROSD_PROBLEM_SUFFIX),
    ):
        entity_id = registry.async_get_entity_id(domain, DOMAIN, f"{ezviz_prefix(entry)}{suffix}")
        if entity_id:
            result[key] = entity_id
    runtime = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    media = media_payload(getattr(getattr(runtime, "ezviz_media", None), "data", None))
    if media is not None:
        result["media"] = media
    controls = controls_payload(getattr(getattr(runtime, "ezviz_controls", None), "data", None))
    if controls is not None:
        result["controls"] = controls
        _prefer_vistoda_entities(hass, registry, entry, result)
    return result


def _prefer_vistoda_entities(hass, registry, entry, result: dict) -> None:
    """With app controls, Vistoda's own alarm panel and battery replace native ones."""
    if not result["controls"]["supported"]:
        return
    owner = account_owner_id(hass, entry)
    runtime = hass.data.get(DOMAIN, {}).get(owner) if owner else None
    if reports_defence(getattr(getattr(runtime, "ezviz_defence", None), "data", None)):
        alarm = registry.async_get_entity_id(
            "alarm_control_panel", DOMAIN, defence_unique_id(owner)
        )
        if alarm:
            result["alarm_entity_id"] = alarm
            result["alarm_scope"] = "account"
    battery = registry.async_get_entity_id(
        "sensor", DOMAIN, f"{ezviz_prefix(entry)}{BATTERY_SUFFIX}"
    )
    if battery and result["controls"]["battery_percent"] is not None:
        result["battery_entity_id"] = battery
