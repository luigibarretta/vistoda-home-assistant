"""Fail-closed NFS backup for standalone provider recordings."""

import asyncio
import hashlib
import json
import os
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from . import BridgeRuntime
from .const import CONF_PROVIDER, DOMAIN, PROVIDER_BLINK, PROVIDER_EZVIZ

BACKUP_MOUNT = Path("/media/vistoda_archives")
BACKUP_ROOT = BACKUP_MOUNT
MAX_BACKUP_BYTES = 256 * 1024 * 1024
MIN_FREE_BYTES = 512 * 1024 * 1024
SAFE_CAMERA = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
SAFE_ID = re.compile(r"^[0-9a-f-]{36}$")
LOCK_KEY = "recording_backup_lock"


@callback
def async_register(hass: HomeAssistant) -> None:
    """Register one administrator-only backup command."""
    websocket_api.async_register_command(hass, ws_backup_recording)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "media_bridge/provider/recordings/backup",
        vol.Required("provider"): vol.In((PROVIDER_BLINK, PROVIDER_EZVIZ)),
        vol.Optional("entry_id", default=""): vol.All(str, vol.Length(max=64)),
        vol.Required("recording_id"): vol.All(str, vol.Match(r"^[0-9a-f-]{36}$")),
    }
)
@websocket_api.async_response
async def ws_backup_recording(hass, connection, msg: dict[str, Any]) -> None:
    """Stream one verified recording to the configured network mount."""
    if not connection.user.is_admin:
        connection.send_error(msg["id"], "unauthorized", "Administrator access required")
        return
    try:
        lock = hass.data.setdefault(DOMAIN, {}).setdefault(LOCK_KEY, asyncio.Lock())
        async with lock:
            manifest, upstream = await _source(hass, msg)
            result = await _backup(hass, msg["provider"], manifest, upstream)
    except Exception:  # Provider clients use integration-specific exception types.
        connection.send_error(msg["id"], "unavailable", "Recording backup is unavailable")
        return
    connection.send_result(msg["id"], result)


async def _source(hass: HomeAssistant, msg: dict[str, Any]):
    recording_id = msg["recording_id"]
    if msg["provider"] == PROVIDER_BLINK:
        runtime = hass.data.get("blink_live_bridge", {}).get("runtime")
        if runtime is None:
            raise ValueError("Blink runtime unavailable")
        payload = await runtime.client.get_json(f"/v1/recordings/{recording_id}")
        manifest = _validate(payload, recording_id, "video/mp2t")
        upstream = await runtime.client.stream(f"/v1/recordings/{recording_id}/media")
        return manifest, upstream
    entry = hass.config_entries.async_get_entry(msg["entry_id"])
    runtime = hass.data.get(DOMAIN, {}).get(msg["entry_id"])
    if (
        entry is None
        or entry.data.get(CONF_PROVIDER) != PROVIDER_EZVIZ
        or not isinstance(runtime, BridgeRuntime)
        or runtime.client is None
    ):
        raise ValueError("EZVIZ runtime unavailable")
    manifest = _validate(
        await runtime.client.provider_recording(recording_id), recording_id, "video/mpeg"
    )
    upstream = await runtime.client.open_provider_recording(recording_id)
    return manifest, upstream


def _validate(manifest: object, recording_id: str, media_type: str) -> dict[str, Any]:
    if (
        not isinstance(manifest, dict)
        or manifest.get("recording_id") != recording_id
        or manifest.get("status") != "ready"
        or manifest.get("media_type") != media_type
        or not SAFE_CAMERA.fullmatch(str(manifest.get("camera", "")))
        or not SAFE_ID.fullmatch(recording_id)
        or not re.fullmatch(r"[0-9a-f]{64}", str(manifest.get("sha256", "")))
        or not isinstance(manifest.get("bytes"), int)
        or not 0 < manifest["bytes"] <= MAX_BACKUP_BYTES
    ):
        raise ValueError("recording is not ready for backup")
    return manifest


async def _backup(hass, provider: str, manifest: dict[str, Any], upstream) -> dict[str, Any]:
    try:
        if upstream.status != 200 or upstream.content_type != manifest["media_type"]:
            raise ValueError("recording media response is invalid")
        target, existing = await hass.async_add_executor_job(_prepare, provider, manifest)
        if existing:
            await hass.async_add_executor_job(
                _write_metadata, target, _metadata(provider, manifest)
            )
            return {"status": "existing", "relative_path": str(target.relative_to(BACKUP_MOUNT))}
        partial = target.with_name(f".{target.name}.partial")
        handle = await hass.async_add_executor_job(_open_partial, partial)
        digest = hashlib.sha256()
        written = 0
        try:
            async for chunk in upstream.content.iter_chunked(512 * 1024):
                written += len(chunk)
                if written > MAX_BACKUP_BYTES or written > manifest["bytes"]:
                    raise ValueError("recording exceeded manifest size")
                digest.update(chunk)
                await hass.async_add_executor_job(handle.write, chunk)
            if written != manifest["bytes"] or digest.hexdigest() != manifest["sha256"]:
                raise ValueError("recording checksum mismatch")
            metadata = _metadata(provider, manifest)
            await hass.async_add_executor_job(_commit, handle, partial, target, metadata)
        except Exception:
            await hass.async_add_executor_job(_discard, handle, partial)
            raise
        return {"status": "created", "relative_path": str(target.relative_to(BACKUP_MOUNT))}
    finally:
        upstream.release()


def _prepare(provider: str, manifest: dict[str, Any]) -> tuple[Path, bool]:
    if not _is_nfs_mount(BACKUP_MOUNT):
        raise OSError("Vistoda network mount is absent")
    camera = manifest["camera"]
    extension = "ts" if provider == PROVIDER_BLINK else "mpegps"
    directory = BACKUP_ROOT / provider / camera
    directory.mkdir(parents=True, exist_ok=True, mode=0o750)
    target = directory / f"{manifest['recording_id']}.{extension}"
    if not target.resolve().is_relative_to(BACKUP_ROOT.resolve()):
        raise OSError("unsafe recording path")
    if target.is_file():
        return target, _sha256(target) == manifest["sha256"]
    target.with_name(f".{target.name}.partial").unlink(missing_ok=True)
    free = shutil.disk_usage(BACKUP_MOUNT).free
    if free < max(MIN_FREE_BYTES, manifest["bytes"] * 2):
        raise OSError("network mount has no safe headroom")
    return target, False


def _is_nfs_mount(path: Path) -> bool:
    """Reject Supervisor state/local-directory false positives."""
    if not path.is_mount():
        return False
    escaped = str(path).replace("\\", "\\134").replace(" ", "\\040")
    try:
        mounts = Path("/proc/self/mounts").read_text(encoding="utf-8")
    except OSError:
        return False
    return any(
        len(fields) >= 3 and fields[1] == escaped and fields[2] in {"nfs", "nfs4"}
        for line in mounts.splitlines()
        if (fields := line.split())
    )


def _open_partial(path: Path):
    return path.open("xb")


def _commit(handle, partial: Path, target: Path, metadata: dict[str, Any]) -> None:
    handle.flush()
    os.fsync(handle.fileno())
    handle.close()
    partial.replace(target)
    _write_metadata(target, metadata)


def _write_metadata(target: Path, metadata: dict[str, Any]) -> None:
    sidecar = target.with_suffix(f"{target.suffix}.json")
    temporary = sidecar.with_name(f".{sidecar.name}.partial")
    temporary.unlink(missing_ok=True)
    with temporary.open("x", encoding="utf-8") as stream:
        json.dump(metadata, stream, sort_keys=True, separators=(",", ":"))
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(sidecar)


def _discard(handle, partial: Path) -> None:
    handle.close()
    partial.unlink(missing_ok=True)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _metadata(provider: str, manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "provider": provider,
        "recording": manifest,
        "backed_up_at": datetime.now(UTC).isoformat(),
    }
