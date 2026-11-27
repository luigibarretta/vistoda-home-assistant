"""Which Blink archives are in use, and the administrator-only switches for them."""

import logging
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from . import BridgeRuntime
from .backup_storage import (
    FEATURE_OPTIONS,
    archive_features,
    configured_mount,
    provider_entry,
    storage_readiness,
)
from .blink_usb_auto_backup import CONF_AUTO_BACKUP
from .runtime import entry_runtime


@callback
def async_register(hass: HomeAssistant) -> None:
    websocket_api.async_register_command(hass, ws_set_auto_backup)
    websocket_api.async_register_command(hass, ws_recording_options)
    websocket_api.async_register_command(hass, ws_set_archive_features)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "media_bridge/blink/recording_options",
        vol.Optional("entry_id", default=""): vol.All(str, vol.Length(max=64)),
    }
)
@websocket_api.async_response
async def ws_recording_options(hass, connection, msg: dict[str, Any]) -> None:
    """Tell the panel which archives are in use (`use_usb` is kept for older panels)."""
    try:
        entry = provider_entry(hass, "blink", msg["entry_id"])
    except ValueError:
        connection.send_error(msg["id"], "not_found", "Blink entry is not available")
        return
    features = archive_features(entry.options)
    connection.send_result(msg["id"], {**features, "use_usb": features["usb"]})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "media_bridge/blink/archive_features/set",
        vol.Optional("entry_id", default=""): vol.All(str, vol.Length(max=64)),
        **{vol.Optional(name): bool for name in FEATURE_OPTIONS},
    }
)
@websocket_api.async_response
async def ws_set_archive_features(hass, connection, msg: dict[str, Any]) -> None:
    """Turn Blink archives on or off; what depends on an archive follows it."""
    if not connection.user.is_admin:
        connection.send_error(msg["id"], "unauthorized", "Administrator access required")
        return
    try:
        entry = provider_entry(hass, "blink", msg["entry_id"])
    except ValueError:
        connection.send_error(msg["id"], "not_found", "Blink entry is not available")
        return
    options = {**entry.options}
    for name, key in FEATURE_OPTIONS.items():
        if name in msg:
            options[key] = msg[name]
    if not archive_features(options)["nfs"]:
        options[CONF_AUTO_BACKUP] = False  # No network backup: nothing to run automatically.
    if not archive_features(options)["local_ha"] and archive_features(entry.options)["local_ha"]:
        await _stop_motion_recording(hass)  # Motion clips are HA-local recordings.
    hass.config_entries.async_update_entry(entry, options=options)
    features = archive_features(options)
    connection.send_result(msg["id"], {**features, "use_usb": features["usb"]})


async def _stop_motion_recording(hass: HomeAssistant) -> None:
    """Best effort: switch off motion recording in the Blink app, keeping its other settings."""
    runtime = hass.data.get("blink_live_bridge", {}).get("runtime")
    if runtime is None:
        return
    try:
        reply = await runtime.client.get_json("/v1/motion/recording")
        settings = reply.get(
            "settings", {}
        )  # {"settings": {...}, "cameras": [...], "poller": {...}}
        if settings.get("enabled"):
            payload = {
                "enabled": False,
                "duration_seconds": settings["duration_seconds"],
                "cameras": settings["cameras"],
            }
            await runtime.client.put_json("/v1/motion/recording", payload)
    except Exception:  # The provider client raises its own error types.
        logging.getLogger(__name__).warning("Motion recording could not be switched off")


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
    if entry is None or not isinstance(entry_runtime(entry), BridgeRuntime):
        connection.send_error(msg["id"], "not_found", "Blink entry is not loaded")
        return
    if msg["enabled"] and not archive_features(entry.options)["nfs"]:
        connection.send_error(msg["id"], "storage_unavailable", "nfs_disabled")
        return
    if msg["enabled"]:
        # Same gate as the options flow: never enable copies onto an unready mount.
        try:
            mount = configured_mount(entry)
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
