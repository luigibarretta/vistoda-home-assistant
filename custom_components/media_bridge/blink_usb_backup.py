"""Fail-closed NFS backup for provider-owned Blink USB clips."""

import asyncio
import hashlib
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .recording_backup import (
    BACKUP_MOUNT,
    BACKUP_ROOT,
    MAX_BACKUP_BYTES,
    MIN_FREE_BYTES,
    _commit,
    _discard,
    _is_nfs_mount,
    _open_partial,
    _sha256,
    _write_metadata,
)

SAFE_CAMERA = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
POSITIVE = vol.All(int, vol.Range(min=1))
LOCK_KEY = "blink_usb_backup_lock"


@callback
def async_register(hass: HomeAssistant) -> None:
    websocket_api.async_register_command(hass, ws_backup_blink_usb)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "media_bridge/blink/usb/backup",
        vol.Required("network_id"): POSITIVE,
        vol.Required("sync_module_id"): POSITIVE,
        vol.Required("manifest_id"): POSITIVE,
        vol.Required("clip_id"): POSITIVE,
        vol.Required("camera"): vol.All(str, vol.Match(SAFE_CAMERA.pattern)),
        vol.Required("created_at"): vol.All(str, vol.Length(max=64)),
        vol.Optional("clip_length_ms"): vol.Any(None, POSITIVE),
    }
)
@websocket_api.async_response
async def ws_backup_blink_usb(hass, connection, msg: dict[str, Any]) -> None:
    """Copy one immutable provider clip without mutating the Blink support."""
    if not connection.user.is_admin:
        connection.send_error(msg["id"], "unauthorized", "Administrator access required")
        return
    try:
        lock = hass.data.setdefault("media_bridge", {}).setdefault(LOCK_KEY, asyncio.Lock())
        async with lock:
            result = await _backup_clip(hass, msg)
    except Exception:
        connection.send_error(msg["id"], "unavailable", "Blink USB backup is unavailable")
        return
    connection.send_result(msg["id"], result)


async def _backup_clip(hass: HomeAssistant, msg: dict[str, Any]) -> dict[str, Any]:
    runtime = hass.data.get("blink_live_bridge", {}).get("runtime")
    if runtime is None:
        raise ValueError("Blink runtime unavailable")
    path = (
        f"/v1/local-storage/{msg['network_id']}/{msg['sync_module_id']}/"
        f"{msg['manifest_id']}/{msg['clip_id']}/media"
    )
    upstream = await runtime.client.stream(path)
    try:
        if upstream.status != 200 or upstream.content_type != "video/mp4":
            raise ValueError("Blink USB media response is invalid")
        if upstream.content_length is not None and upstream.content_length > MAX_BACKUP_BYTES:
            raise ValueError("Blink USB clip exceeds backup limit")
        target, existing = await hass.async_add_executor_job(_prepare, msg)
        if existing:
            metadata = await hass.async_add_executor_job(_existing_metadata, target, msg)
            await hass.async_add_executor_job(_write_metadata, target, metadata)
            return {"status": "existing", "relative_path": _relative(target)}
        partial = target.with_name(f".{target.name}.partial")
        handle = await hass.async_add_executor_job(_open_partial, partial)
        digest = hashlib.sha256()
        written = 0
        try:
            async for chunk in upstream.content.iter_chunked(512 * 1024):
                written += len(chunk)
                if written > MAX_BACKUP_BYTES:
                    raise ValueError("Blink USB clip exceeds backup limit")
                digest.update(chunk)
                await hass.async_add_executor_job(handle.write, chunk)
            if written == 0:
                raise ValueError("Blink USB clip is empty")
            metadata = _metadata(msg, written, digest.hexdigest())
            await hass.async_add_executor_job(_commit, handle, partial, target, metadata)
        except Exception:
            await hass.async_add_executor_job(_discard, handle, partial)
            raise
        return {"status": "created", "relative_path": _relative(target)}
    finally:
        upstream.release()


def _prepare(msg: dict[str, Any]) -> tuple[Path, bool]:
    if not _is_nfs_mount(BACKUP_MOUNT):
        raise OSError("Vistoda network mount is absent")
    directory = BACKUP_ROOT / "blink-usb" / msg["camera"]
    directory.mkdir(parents=True, exist_ok=True, mode=0o750)
    target = directory / f"{msg['manifest_id']}-{msg['clip_id']}.mp4"
    if not target.resolve().is_relative_to(BACKUP_ROOT.resolve()):
        raise OSError("unsafe Blink USB backup path")
    if target.is_file():
        return target, True
    target.with_name(f".{target.name}.partial").unlink(missing_ok=True)
    if shutil.disk_usage(BACKUP_MOUNT).free < MIN_FREE_BYTES:
        raise OSError("network mount has no safe headroom")
    return target, False


def _existing_metadata(target: Path, msg: dict[str, Any]) -> dict[str, Any]:
    size = target.stat().st_size
    if not 0 < size <= MAX_BACKUP_BYTES:
        raise OSError("existing Blink USB backup is invalid")
    return _metadata(msg, size, _sha256(target))


def _metadata(msg: dict[str, Any], size: int, digest: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "provider": "blink-usb",
        "source": {
            "network_id": msg["network_id"],
            "sync_module_id": msg["sync_module_id"],
            "manifest_id": msg["manifest_id"],
            "clip_id": msg["clip_id"],
            "camera": msg["camera"],
            "created_at": msg["created_at"],
            "clip_length_ms": msg.get("clip_length_ms"),
        },
        "bytes": size,
        "sha256": digest,
        "backed_up_at": datetime.now(UTC).isoformat(),
    }


def _relative(target: Path) -> str:
    return str(target.relative_to(BACKUP_MOUNT))
