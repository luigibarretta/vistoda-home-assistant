"""Secret-free Home Assistant diagnostics for one Vistoda entry."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.redact import async_redact_data

from . import BridgeRuntime
from .backup_storage import configured_mount, storage_readiness
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
        "config_entry": async_redact_data(
            dict(entry.data),
            TO_REDACT
            | {
                "ring_device_id",
                "ring_official_binding",
                "password",
                "email",
                "account",
                "verification_code",
                "refresh_token",
                "access_token",
            },
        ),
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
    if entry.data.get(CONF_PROVIDER) in {"blink", "ezviz"}:
        try:
            payload["backup_storage"] = await hass.async_add_executor_job(
                storage_readiness, configured_mount(entry)
            )
        except (ValueError, OSError):
            payload["backup_storage"] = {"ready": False, "reason": "invalid_storage_name"}
    payload["reauth_supported"] = entry.data.get(CONF_PROVIDER) in {"ring", "ezviz"}
    if runtime and runtime.ring_status:
        payload["ring_status"] = {
            "last_update_success": runtime.ring_status.last_update_success,
            "has_data": runtime.ring_status.data is not None,
        }
    if runtime and runtime.ring_events:
        payload["ring_events"] = {"connected": runtime.ring_events.connected}
    return payload
