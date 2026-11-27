"""Blink HA-local recordings are stored as MP4: smaller, and playable by any player.

The app's archive keeps MPEG-TS. The copy in the chosen folder is the same video and
audio packets in an MP4 file (no re-encoding). The checksum of the original recording
stays in the metadata, so a recording that was already copied is recognised, and the MP4's
own size and checksum are verified when it is read back.
"""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .ts_remux import ts_to_mp4

SOURCE_TYPE = "video/mp2t"
MP4_TYPE = "video/mp4"


def wants_mp4(provider: str, manifest: dict[str, Any]) -> bool:
    return provider == "blink" and manifest["media_type"] == SOURCE_TYPE


def existing_mp4(target: Path, manifest: dict[str, Any]) -> bool:
    """True when this recording is already stored at `target`; False to (re)create it.

    A file whose metadata is missing is an interrupted copy and is replaced. A file whose
    metadata names another recording is never overwritten.
    """
    if not target.is_file():
        return False
    sidecar = target.with_suffix(".mp4.json")
    if not sidecar.is_file() or sidecar.is_symlink() or sidecar.stat().st_size > 16384:
        return False
    metadata = json.loads(sidecar.read_text(encoding="utf-8"))
    stored = metadata.get("stored", {})
    if (
        metadata.get("recording", {}).get("sha256") != manifest["sha256"]
        or stored.get("bytes") != target.stat().st_size
    ):
        raise OSError("existing backup belongs to a different recording")
    return True


def convert(data: bytes) -> bytes | None:
    """The MP4 for a verified TS recording, or None to keep the original TS."""
    try:
        return ts_to_mp4(data)
    except ValueError:
        return None


def mp4_metadata(manifest: dict[str, Any], mp4: bytes) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "provider": "blink",
        "recording": manifest,
        "stored": {
            "media_type": MP4_TYPE,
            "bytes": len(mp4),
            "sha256": hashlib.sha256(mp4).hexdigest(),
        },
        "backed_up_at": datetime.now(UTC).isoformat(),
    }


async def read_verified(upstream, manifest: dict[str, Any], limit: int) -> bytes:
    """The whole recording, only when its size and checksum match the manifest."""
    chunks: list[bytes] = []
    digest = hashlib.sha256()
    written = 0
    async for chunk in upstream.content.iter_chunked(512 * 1024):
        written += len(chunk)
        if written > limit or written > manifest["bytes"]:
            raise ValueError("recording exceeded manifest size")
        digest.update(chunk)
        chunks.append(chunk)
    if written != manifest["bytes"] or digest.hexdigest() != manifest["sha256"]:
        raise ValueError("recording checksum mismatch")
    return b"".join(chunks)


async def store_mp4(hass, provider, manifest, upstream, mount, target) -> dict[str, Any]:
    """Copy a Blink recording as MP4; the original TS is kept if it cannot be converted."""
    from . import recording_backup as backup  # Imported late: backup imports this module.

    data = await read_verified(upstream, manifest, backup.MAX_BACKUP_BYTES)
    mp4 = await hass.async_add_executor_job(convert, data)
    if mp4 is None:
        target, body = target.with_suffix(".ts"), data
        metadata = backup._metadata(provider, manifest)
    else:
        body, metadata = mp4, mp4_metadata(manifest, mp4)
    await hass.async_add_executor_job(_write_file, backup, target, body, metadata)
    return {"status": "created", "relative_path": str(target.relative_to(mount))}


def _write_file(backup, target: Path, body: bytes, metadata: dict[str, Any]) -> None:
    handle, partial = backup.open_private_partial(target)
    try:
        handle.write(body)
        backup._commit(handle, partial, target, metadata)
    except BaseException:
        backup._discard(handle, partial)
        raise
