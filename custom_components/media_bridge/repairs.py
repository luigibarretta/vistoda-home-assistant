"""Create and clear non-secret Vistoda issues in Home Assistant Repairs."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import CONF_PROVIDER, DOMAIN


def update_bridge_issue(hass: HomeAssistant, entry: ConfigEntry, available: bool) -> None:
    """Reflect bridge reachability without persisting endpoint details."""
    issue_id = f"bridge_unavailable_{entry.entry_id}"
    if available:
        ir.async_delete_issue(hass, DOMAIN, issue_id)
        return
    provider = str(entry.data.get(CONF_PROVIDER, "unknown")).upper()
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key="bridge_unavailable",
        translation_placeholders={"provider": provider},
    )


def update_ring_push_issue(hass: HomeAssistant, entry: ConfigEntry, available: bool) -> None:
    """Reflect native Ring push health without exposing its transport details."""
    issue_id = f"ring_push_unavailable_{entry.entry_id}"
    if available:
        ir.async_delete_issue(hass, DOMAIN, issue_id)
        return
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key="ring_push_unavailable",
    )
