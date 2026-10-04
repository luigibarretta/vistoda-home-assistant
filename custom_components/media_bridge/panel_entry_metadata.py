"""Vistoda-owned entity references and cached media status for panel entries."""

from homeassistant.helpers import entity_registry as er

from .const import DOMAIN, PROVIDER_EZVIZ, PROVIDER_RING
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
    return result
