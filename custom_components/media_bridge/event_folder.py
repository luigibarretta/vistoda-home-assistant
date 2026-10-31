"""Where one camera's archived events live, and safe reads of those folders.

A folder is `<mount>/events/<provider>/<camera>` in the Vistoda archive or
`<mount>/<device>/_events` in SceneTrove's shared device folder.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

from . import backup_storage

ROOT = "events"
SHARED_ROOT = "_events"


@dataclass(frozen=True)
class EventFolder:
    """One camera's events: `parts` under the mount; records name provider and camera."""

    mount: Path
    provider: str
    camera: str
    parts: tuple[str, ...]


def vistoda_folder(mount: Path, provider: str, camera: str) -> EventFolder:
    return EventFolder(mount, provider, camera, (ROOT, provider, camera))


def shared_folder(mount: Path, device: str, provider: str, camera: str) -> EventFolder:
    """SceneTrove's `<device>/_events`, which SceneTrove only reads."""
    return EventFolder(mount, provider, camera, (device, SHARED_ROOT))


def camera_directory(folder: EventFolder) -> Path | None:
    if backup_storage.network_filesystem(folder.mount, writable=False) is None:
        raise ValueError("network mount missing")
    current = folder.mount
    for part in folder.parts:
        if not backup_storage.SAFE_PART.fullmatch(part):
            raise ValueError("invalid archive path")
        current = current / part
        if current.is_symlink() or not current.is_dir():
            return None
    return current


def directories(folders: Sequence[EventFolder]) -> Iterator[tuple[EventFolder, Path]]:
    """Existing folders; a missing mount fails only when no folder is readable."""
    readable = 0
    for folder in folders:
        try:
            directory = camera_directory(folder)
        except ValueError:
            continue
        readable += 1
        if directory is not None:
            yield folder, directory
    if not readable:
        raise ValueError("network mount missing")


def regular_file(directory: Path, *parts: str) -> Path | None:
    """A regular file under `directory`, never through a symlink."""
    path = directory
    for part in parts:
        path = path / part
        if path.is_symlink():
            return None
    return path if path.is_file() else None
