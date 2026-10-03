"""Administrator-only switch for the hourly Blink network backup."""

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from . import BridgeRuntime
from .backup_storage import (
    CONF_BACKUP_STORAGE,
    DEFAULT_BACKUP_STORAGE,
    provider_entry,
    storage_mount,
    storage_readiness,
)
from .blink_usb_auto_backup import CONF_AUTO_BACKUP
from .const import DOMAIN


@callback
def async_register(hass: HomeAssistant) -> None:
    websocket_api.async_register_command(hass, ws_set_auto_backup)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "media_bridge/blink/auto_backup/set",
        vol.Required("entry_id"): vol.All(str, vol.Length(min=1, max=64)),
        vol.Required("enabled"): bool,
    }
)
@websocket_api.async_response
async def ws_set_auto_backup(hass, connection, msg: dict[str, Any]) -> None:
    """Persist the option; the hourly worker reads it live, so no reload is needed."""
    if not connection.user.is_admin:
        connection.send_error(msg["id"], "unauthorized", "Administrator access required")
        return
    try:
        entry = provider_entry(hass, "blink", msg["entry_id"])
    except ValueError:
        entry = None
    if entry is None or not isinstance(
        hass.data.get(DOMAIN, {}).get(entry.entry_id), BridgeRuntime
    ):
        connection.send_error(msg["id"], "not_found", "Blink entry is not loaded")
        return
    if msg["enabled"]:
        # Same gate as the options flow: never enable copies onto an unready mount.
        try:
            mount = storage_mount(entry.options.get(CONF_BACKUP_STORAGE, DEFAULT_BACKUP_STORAGE))
        except ValueError:
            readiness = {"ready": False, "reason": "invalid_storage_name"}
        else:
            readiness = await hass.async_add_executor_job(storage_readiness, mount)
        if not readiness["ready"]:
            connection.send_error(msg["id"], "storage_unavailable", readiness["reason"])
            return
    hass.config_entries.async_update_entry(
        entry, options={**entry.options, CONF_AUTO_BACKUP: msg["enabled"]}
    )
    connection.send_result(msg["id"], {"entry_id": entry.entry_id, "enabled": msg["enabled"]})
