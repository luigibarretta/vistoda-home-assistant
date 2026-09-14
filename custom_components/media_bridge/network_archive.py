"""Inventory only completed Vistoda backups on the configured network mount."""

import hashlib
import json
import re
from pathlib import Path

from .backup_storage import network_filesystem

MAX_ITEMS = 10000
MAX_BYTES = 256 * 1024 * 1024
SAFE_PATH = re.compile(r"^(blink-usb|blink)/[A-Za-z0-9_-]{1,64}/[0-9a-f-]+\.(mp4|ts)$")


def checked_file(mount: Path, relative: str, *, checksum=False):
    """Never traverse a symlink, local fallback or unowned backup subtree."""
    if not SAFE_PATH.fullmatch(relative) or network_filesystem(mount) is None:
        raise ValueError("network archive unavailable")
    target = mount
    for part in Path(relative).parts:
        target = target / part
        if target.is_symlink():
            raise ValueError("unsafe backup path")
    sidecar = target.with_suffix(target.suffix + ".json")
    if sidecar.is_symlink() or sidecar.stat().st_size > 16384:
        raise ValueError("unsafe backup metadata")
    metadata = json.loads(sidecar.read_text(encoding="utf-8"))
    if metadata.get("schema_version") != 1:
        raise ValueError("unsupported backup metadata")
    usb = relative.startswith("blink-usb/")
    if metadata.get("provider") != ("blink-usb" if usb else "blink"):
        raise ValueError("backup provider mismatch")
    source = metadata.get("source" if usb else "recording", {})
    if not isinstance(source, dict):
        raise ValueError("invalid backup metadata")
    expected_name = (
        f"{source.get('manifest_id')}-{source.get('clip_id')}.mp4"
        if usb
        else f"{source.get('recording_id')}.ts"
    )
    if target.name != expected_name or target.parent.name != source.get("camera"):
        raise ValueError("backup identity mismatch")
    integrity = metadata if usb else source
    size, digest = integrity.get("bytes"), integrity.get("sha256")
    if type(size) is not int or not 0 < size <= MAX_BYTES or target.stat().st_size != size:
        raise ValueError("backup size mismatch")
    if not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest):
        raise ValueError("backup checksum absent")
    if checksum:
        with target.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != digest:
                raise ValueError("backup checksum mismatch")
    media_id = (
        "usb:"
        + ":".join(
            str(source.get(key, ""))
            for key in ("network_id", "sync_module_id", "manifest_id", "clip_id")
        )
        if usb
        else f"local:{source.get('recording_id', '')}"
    )
    if not re.fullmatch(r"(?:usb:\d+:\d+:\d+:\d+|local:[0-9a-f-]{36})", media_id):
        raise ValueError("invalid source identity")
    return target, {
        "id": relative,
        "media_id": media_id,
        "camera": str(source.get("camera", "")),
        "created_at": source.get("created_at" if usb else "requested_at", ""),
        "backed_up_at": metadata.get("backed_up_at", ""),
        "bytes": size,
        "media_type": "video/mp4" if usb else "video/mp2t",
    }


def inventory(mount: Path, page: int, page_size: int, camera: str = "", members=None):
    if network_filesystem(mount) is None:
        raise ValueError("network mount missing")
    items, cameras, scanned = [], set(), 0
    for provider in ("blink-usb", "blink"):
        root = mount / provider
        if root.is_symlink() or not root.is_dir():
            continue
        for directory in root.iterdir():
            scanned += 1
            if scanned > MAX_ITEMS * 2:
                raise ValueError("network archive inventory limit exceeded")
            if directory.is_symlink() or not directory.is_dir():
                continue
            for sidecar in directory.iterdir():
                scanned += 1
                if scanned > MAX_ITEMS * 2:
                    raise ValueError("network archive inventory limit exceeded")
                if not sidecar.name.endswith((".mp4.json", ".ts.json")):
                    continue
                relative = str(sidecar.relative_to(mount))[:-5]
                try:
                    _, item = checked_file(mount, relative)
                except (ValueError, OSError, TypeError, AttributeError):
                    continue
                cameras.add(item["camera"])
                if (not camera or camera == item["camera"]) and (
                    members is None or item["media_id"] in members
                ):
                    items.append(item)
    items.sort(key=lambda item: (item["created_at"], item["id"]), reverse=True)
    pages = max(1, (len(items) + page_size - 1) // page_size)
    page = min(page, pages)
    return {
        "items": items[(page - 1) * page_size : page * page_size],
        "cameras": sorted(cameras),
        "directory": str(mount),
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_items": len(items),
            "total_pages": pages,
            "has_previous": page > 1,
            "has_next": page < pages,
        },
    }
