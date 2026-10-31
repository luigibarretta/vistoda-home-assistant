"""Provider-neutral camera event archive on the Vistoda network storage.

Layout: `<folder>/<YYYY>/<MM>/<stamp>-<alarm_id>.json` with the picture next
to it as `.jpg`, where the folder is `<mount>/events/<provider>/<camera>` or,
shared with SceneTrove, `<mount>/<device>/_events`. Writes are atomic and
idempotent; reads never follow a symlink or leave the mount, skip foreign
files and merge a camera's folders by event name.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from collections.abc import Iterator, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from . import backup_storage
from .event_folder import EventFolder, directories, regular_file
from .event_folder import shared_folder as shared_folder  # re-exported for callers
from .event_folder import vistoda_folder as vistoda_folder  # re-exported for callers

SCHEMA_VERSION = 1
MAX_METADATA_BYTES = 16 * 1024
MAX_SCANNED = 200_000
SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,96}$")
EVENT_NAME = re.compile(r"^(\d{4})(\d{2})\d{2}T\d{6}Z-[A-Za-z0-9_-]{1,96}$")
DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# Left by a deletion so a backfill never archives the event again; never pruned.
DELETED = ".deleted"


def event_id(occurred_at: int, alarm_id: str) -> str:
    """Archive name of one event; sorts by time."""
    if not SAFE_ID.fullmatch(alarm_id):
        raise ValueError("invalid alarm id")
    return f"{datetime.fromtimestamp(occurred_at, UTC):%Y%m%dT%H%M%SZ}-{alarm_id}"


def write_event(where: EventFolder, alarm: dict[str, Any], jpeg: bytes | None) -> bool:
    """Archive one alarm and its picture; False when it is already archived."""
    occurred_at = int(alarm["occurred_at"])
    name = event_id(occurred_at, alarm["alarm_id"])
    moment = datetime.fromtimestamp(occurred_at, UTC)
    folder = backup_storage.safe_directory(
        where.mount, *where.parts, f"{moment:%Y}", f"{moment:%m}"
    )
    target = folder / f"{name}.json"
    if target.exists():
        return False
    picture = f"{name}.jpg" if jpeg else None
    if picture:
        _atomic_write(folder / picture, jpeg)
    record = {
        "schema_version": SCHEMA_VERSION,
        "provider": where.provider,
        "camera": where.camera,
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


def has_event(folders: Sequence[EventFolder], occurred_at: int, alarm_id: str) -> bool:
    """Whether this alarm is archived, or was deleted, in any folder (no listing)."""
    name = event_id(occurred_at, alarm_id)
    moment = datetime.fromtimestamp(occurred_at, UTC)
    return any(
        regular_file(directory, f"{moment:%Y}", f"{moment:%m}", f"{name}{suffix}") is not None
        for _folder, directory in directories(folders)
        for suffix in (".json", DELETED)
    )


def list_events(
    folders: Sequence[EventFolder], page: int, page_size: int, day: str = ""
) -> dict[str, Any]:
    """One page of archived events, newest first; `day` is a UTC `YYYY-MM-DD`.

    Names sort by time, so only the records of the requested page are read; an
    event in several folders is listed once, from the first folder.
    """
    if day and not DAY.fullmatch(day):
        raise ValueError("invalid day")
    prefix = day.replace("-", "")
    found = {}
    for folder, path in _event_paths(folders):
        if path.stem.startswith(prefix):
            found.setdefault(path.stem, (folder, path))
    paths = [found[name] for name in sorted(found, reverse=True)]
    pages = max(1, -(-len(paths) // page_size))
    page = min(max(page, 1), pages)
    shown = paths[(page - 1) * page_size : page * page_size]
    return {
        "items": [item for folder, path in shown if (item := _read(path, folder)) is not None],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_items": len(paths),
            "total_pages": pages,
            "has_previous": page > 1,
            "has_next": page < pages,
        },
    }


def event_picture(folders: Sequence[EventFolder], event: str) -> Path:
    """Checked path of an archived picture, from the first folder that has it."""
    match = EVENT_NAME.fullmatch(event)
    if match is None:
        raise ValueError("unknown event picture")
    for _folder, directory in directories(folders):
        if (path := regular_file(directory, *match.groups(), f"{event}.jpg")) is not None:
            return path
    raise ValueError("unknown event picture")


def delete_event(folders: Sequence[EventFolder], event: str) -> bool:
    """Delete one of this camera's archived events from every folder, leaving a marker.

    False when absent; a record of another camera sharing the folder is kept.
    """
    match = EVENT_NAME.fullmatch(event)
    if match is None:
        return False
    removed = False
    for folder, directory in directories(folders):
        record = regular_file(directory, *match.groups(), f"{event}.json")
        if record is None or _read(record, folder) is None:
            continue
        record.with_suffix(".jpg").unlink(missing_ok=True)
        _atomic_write(record.with_suffix(DELETED), b"")
        record.unlink()
        removed = True
    return removed


def prune_events(folders: Sequence[EventFolder], older_than: int) -> int:
    """Delete archived events (JSON and picture) older than `older_than`, by name."""
    cutoff = f"{datetime.fromtimestamp(older_than, UTC):%Y%m%dT%H%M%SZ}"
    removed = 0
    for folder, path in _event_paths(folders):
        if path.stem[:16] < cutoff and _read(path, folder) is not None:
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
            # Readable by SceneTrove, which serves the shared folder's events.
            os.fchmod(stream.fileno(), 0o644)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


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


def _event_paths(folders: Sequence[EventFolder]) -> list[tuple[EventFolder, Path]]:
    return [
        (folder, path)
        for folder, directory in directories(folders)
        for path in _event_files(directory)
    ]


def _read(path: Path, folder: EventFolder) -> dict[str, Any] | None:
    try:
        if path.is_symlink() or path.stat().st_size > MAX_METADATA_BYTES:
            return None
        record = json.loads(path.read_text(encoding="utf-8"))
        identity = event_id(record["occurred_at"], record["alarm_id"])
    except (OSError, ValueError, TypeError, KeyError, OverflowError):
        return None
    if (
        record.get("schema_version") != SCHEMA_VERSION
        or record.get("provider") != folder.provider
        or record.get("camera") != folder.camera
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
