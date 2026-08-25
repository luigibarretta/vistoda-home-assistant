"""Secret-free Home Assistant diagnostics for one Vistoda entry."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.redact import async_redact_data

from . import BridgeRuntime
from .const import (
    CONF_ALIAS,
    CONF_API_TOKEN,
    CONF_MANAGED_APP,
    CONF_PROVIDER,
    CONF_URL,
    DOMAIN,
    INTEGRATION_VERSION,
)

TO_REDACT = {CONF_ALIAS, CONF_API_TOKEN, CONF_URL}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return bounded operational evidence without private connection data."""
    runtime: BridgeRuntime | None = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    coordinator = runtime.coordinator if runtime else None
    payload: dict[str, Any] = {
        "integration_version": INTEGRATION_VERSION,
        "config_entry": async_redact_data(dict(entry.data), TO_REDACT),
        "provider": entry.data.get(CONF_PROVIDER, "unknown"),
        "managed_app": bool(entry.data.get(CONF_MANAGED_APP)),
        "loaded": runtime is not None,
        "coordinator": {
            "last_update_success": bool(
                coordinator is not None and coordinator.last_update_success
            ),
            "data_kind": type(coordinator.data).__name__ if coordinator else "none",
        },
    }
    if runtime and runtime.ring_status:
        payload["ring_status"] = {
            "last_update_success": runtime.ring_status.last_update_success,
            "has_data": runtime.ring_status.data is not None,
        }
    if runtime and runtime.ring_events:
        payload["ring_events"] = {"connected": runtime.ring_events.connected}
    return payload
