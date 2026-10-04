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


def update_ezviz_binding_issue(hass: HomeAssistant, entry: ConfigEntry, available: bool) -> None:
    """Explain an unavailable or changed physical EZVIZ camera binding."""
    issue_id = f"ezviz_binding_unavailable_{entry.entry_id}"
    if available:
        ir.async_delete_issue(hass, DOMAIN, issue_id)
        return
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=False,
        severity=ir.IssueSeverity.ERROR,
        translation_key="ezviz_binding_unavailable",
    )


def update_ring_push_silent_issue(hass: HomeAssistant, entry: ConfigEntry, degraded: bool) -> None:
    """Warn when Ring stopped delivering call notifications to the engine."""
    issue_id = f"ring_push_silent_{entry.entry_id}"
    if not degraded:
        ir.async_delete_issue(hass, DOMAIN, issue_id)
        return
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key="ring_push_silent",
        translation_placeholders={"name": entry.title},
    )


def update_ezviz_core_issue(hass: HomeAssistant, available: bool) -> None:
    """Explain that EZVIZ settings and arming need the native EZVIZ integration."""
    issue_id = "ezviz_core_unavailable"
    if available:
        ir.async_delete_issue(hass, DOMAIN, issue_id)
        return
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key="ezviz_core_unavailable",
    )
