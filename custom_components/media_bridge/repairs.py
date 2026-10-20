"""Create and clear non-secret Vistoda issues in Home Assistant Repairs.

Household automations turn every new issue into a phone alert, so issues caused
by an outage wait for the continuous-outage grace; a single success clears them.
"""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import CONF_PROVIDER, DOMAIN
from .outage import forget_outages, outage_clock

# Names as the household sees them in Settings → Apps.
PROVIDER_NAMES = {"ring": "Ring", "ezviz": "EZVIZ", "blink": "Blink"}
# Per-entry issue ids are f"{prefix}{entry_id}".
ENTRY_ISSUE_PREFIXES = (
    "bridge_unavailable_",
    "ring_push_unavailable_",
    "ring_push_silent_",
    "ezviz_binding_unavailable_",
)


def _clear(hass: HomeAssistant, issue_id: str) -> None:
    outage_clock(issue_id).up()
    ir.async_delete_issue(hass, DOMAIN, issue_id)


def update_bridge_issue(hass: HomeAssistant, entry: ConfigEntry, available: bool) -> None:
    """Reflect a lasting bridge outage without persisting endpoint details."""
    issue_id = f"bridge_unavailable_{entry.entry_id}"
    if available:
        _clear(hass, issue_id)
        return
    if not outage_clock(issue_id).down():
        return
    provider = str(entry.data.get(CONF_PROVIDER, "unknown"))
    provider = PROVIDER_NAMES.get(provider, provider.upper())
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


def update_ezviz_binding_issue(
    hass: HomeAssistant, entry: ConfigEntry, available: bool, *, mismatch: bool = False
) -> None:
    """Explain a changed binding at once, an unverifiable one only when it lasts."""
    issue_id = f"ezviz_binding_unavailable_{entry.entry_id}"
    if available:
        _clear(hass, issue_id)
        return
    if not mismatch and not outage_clock(issue_id).down():
        return
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=False,
        severity=ir.IssueSeverity.ERROR if mismatch else ir.IssueSeverity.WARNING,
        translation_key="ezviz_binding_mismatch" if mismatch else "ezviz_binding_unavailable",
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
    """Explain that delegated EZVIZ controls lost the native EZVIZ integration."""
    issue_id = "ezviz_core_unavailable"
    if available:
        _clear(hass, issue_id)
        return
    # Native entries retry their own cloud login (setup_retry) or reload briefly.
    if not outage_clock(issue_id).down():
        return
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key="ezviz_core_unavailable",
    )


def remove_entry_issues(hass: HomeAssistant, entry_id: str, *, forget: bool = False) -> None:
    """Delete one entry's issues; `forget` also drops its outage clocks (entry removed)."""
    for prefix in ENTRY_ISSUE_PREFIXES:
        ir.async_delete_issue(hass, DOMAIN, f"{prefix}{entry_id}")
    if forget:
        forget_outages(f"_{entry_id}")
