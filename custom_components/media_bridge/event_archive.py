"""Provider-neutral camera event archive on the Vistoda network storage.

Layout: `<mount>/events/<provider>/<camera>/<YYYY>/<MM>/<stamp>-<alarm_id>.json`
with the picture next to it as `.jpg`. Writes are atomic and idempotent;
reads never follow a symlink or leave the mount, and skip foreign files.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from . import backup_storage

ROOT = "events"
SCHEMA_VERSION = 1
MAX_METADATA_BYTES = 16 * 1024
MAX_SCANNED = 200_000
SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,96}$")
EVENT_NAME = re.compile(r"^(\d{4})(\d{2})\d{2}T\d{6}Z-[A-Za-z0-9_-]{1,96}$")
DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def event_id(occurred_at: int, alarm_id: str) -> str:
    """Archive name of one event; sorts by time."""
    if not SAFE_ID.fullmatch(alarm_id):
        raise ValueError("invalid alarm id")
    return f"{datetime.fromtimestamp(occurred_at, UTC):%Y%m%dT%H%M%SZ}-{alarm_id}"


def write_event(
    mount: Path, provider: str, camera: str, alarm: dict[str, Any], jpeg: bytes | None
) -> bool:
    """Archive one alarm and its picture; False when it is already archived."""
    occurred_at = int(alarm["occurred_at"])
    name = event_id(occurred_at, alarm["alarm_id"])
    moment = datetime.fromtimestamp(occurred_at, UTC)
    folder = backup_storage.safe_directory(
        mount, ROOT, provider, camera, f"{moment:%Y}", f"{moment:%m}"
    )
    target = folder / f"{name}.json"
    if target.exists():
        return False
    picture = f"{name}.jpg" if jpeg else None
    if picture:
        _atomic_write(folder / picture, jpeg)
    record = {
        "schema_version": SCHEMA_VERSION,
        "provider": provider,
        "camera": camera,
        "alarm_id": alarm["alarm_id"],
        "occurred_at": occurred_at,
        "category": str(alarm.get("category") or "other"),
        "alarm_type": int(alarm.get("alarm_type") or 0),
        "title": str(alarm.get("title") or "")[:160],
        "picture": picture,
        "archived_at": datetime.now(UTC).isoformat(),
    }
    _atomic_write(target, json.dumps(record, sort_keys=True, separators=(",", ":")).encode())
    return True


def has_event(mount: Path, provider: str, camera: str, occurred_at: int, alarm_id: str) -> bool:
    """Whether this alarm is already archived (no listing, no directory created)."""
    name = event_id(occurred_at, alarm_id)
    directory = _camera_directory(mount, provider, camera)
    if directory is None:
        return False
    moment = datetime.fromtimestamp(occurred_at, UTC)
    path = directory
    for part in (f"{moment:%Y}", f"{moment:%m}", f"{name}.json"):
        path = path / part
        if path.is_symlink():
            return False
    return path.is_file()


def list_events(
    mount: Path, provider: str, camera: str, page: int, page_size: int, day: str = ""
) -> dict[str, Any]:
    """One page of archived events, newest first; `day` is a UTC `YYYY-MM-DD`.

    Names sort by time, so only the records of the requested page are read.
    """
    if day and not DAY.fullmatch(day):
        raise ValueError("invalid day")
    prefix = day.replace("-", "")
    paths = sorted(
        (path for path in _event_paths(mount, provider, camera) if path.stem.startswith(prefix)),
        key=lambda path: path.stem,
        reverse=True,
    )
    pages = max(1, -(-len(paths) // page_size))
    page = min(max(page, 1), pages)
    shown = paths[(page - 1) * page_size : page * page_size]
    return {
        "items": [item for path in shown if (item := _read(path, provider, camera)) is not None],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_items": len(paths),
            "total_pages": pages,
            "has_previous": page > 1,
            "has_next": page < pages,
        },
    }


def event_picture(mount: Path, provider: str, camera: str, event: str) -> Path:
    """Checked path of an archived picture."""
    match = EVENT_NAME.fullmatch(event)
    directory = _camera_directory(mount, provider, camera)
    if match is None or directory is None:
        raise ValueError("unknown event picture")
    path = directory
    for part in (*match.groups(), f"{event}.jpg"):
        path = path / part
        if path.is_symlink():
            raise ValueError("unsafe event picture")
    if not path.is_file():
        raise ValueError("unknown event picture")
    return path


def prune_events(mount: Path, provider: str, camera: str, older_than: int) -> int:
    """Delete archived events (JSON and picture) older than `older_than`, by name."""
    cutoff = f"{datetime.fromtimestamp(older_than, UTC):%Y%m%dT%H%M%SZ}"
    removed = 0
    for path in _event_paths(mount, provider, camera):
        if path.stem[:16] < cutoff:
            path.with_suffix(".jpg").unlink(missing_ok=True)
            path.unlink(missing_ok=True)
            removed += 1
    return removed


def _atomic_write(path: Path, data: bytes) -> None:
    """Write through a temporary file private to this writer, then rename."""
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".partial", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def _camera_directory(mount: Path, provider: str, camera: str) -> Path | None:
    if backup_storage.network_filesystem(mount, writable=False) is None:
        raise ValueError("network mount missing")
    current = mount
    for part in (ROOT, provider, camera):
        if not backup_storage.SAFE_PART.fullmatch(part):
            raise ValueError("invalid archive path")
        current = current / part
        if current.is_symlink() or not current.is_dir():
            return None
    return current


def _event_files(directory: Path) -> Iterator[Path]:
    scanned = 0
    for year in directory.iterdir():
        if year.is_symlink() or not year.is_dir() or not year.name.isdigit():
            continue
        for month in year.iterdir():
            if month.is_symlink() or not month.is_dir() or not month.name.isdigit():
                continue
            for path in month.iterdir():
                scanned += 1
                if scanned > MAX_SCANNED:
                    raise ValueError("event archive scan limit exceeded")
                if path.suffix == ".json" and EVENT_NAME.fullmatch(path.stem):
                    yield path


def _event_paths(mount: Path, provider: str, camera: str) -> list[Path]:
    directory = _camera_directory(mount, provider, camera)
    return [] if directory is None else list(_event_files(directory))


def _read(path: Path, provider: str, camera: str) -> dict[str, Any] | None:
    try:
        if path.is_symlink() or path.stat().st_size > MAX_METADATA_BYTES:
            return None
        record = json.loads(path.read_text(encoding="utf-8"))
        identity = event_id(record["occurred_at"], record["alarm_id"])
    except (OSError, ValueError, TypeError, KeyError, OverflowError):
        return None
    if (
        record.get("schema_version") != SCHEMA_VERSION
        or record.get("provider") != provider
        or record.get("camera") != camera
        or type(record["occurred_at"]) is not int
        or identity != path.stem
    ):
        return None
    picture = path.with_suffix(".jpg")
    alarm_type = record.get("alarm_type")
    return {
        "id": path.stem,
        "alarm_id": record["alarm_id"],
        "occurred_at": record["occurred_at"],
        "category": str(record.get("category") or "other"),
        "alarm_type": alarm_type if type(alarm_type) is int else 0,
        "title": str(record.get("title") or "")[:160],
        "picture": record.get("picture") == picture.name
        and picture.is_file()
        and not picture.is_symlink(),
    }
