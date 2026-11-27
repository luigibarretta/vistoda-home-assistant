"""Validated Home Assistant network-storage configuration and redacted readiness."""

import os
import re
import shutil
from pathlib import Path

from .const import CONF_PROVIDER, DOMAIN, PROVIDER_BLINK, PROVIDER_EZVIZ

CONF_BACKUP_STORAGE = "backup_storage"
CONF_BACKUP_ALLOW_LOCAL = "backup_allow_local"
CONF_USE_USB = "blink_use_usb"
CONF_USE_LOCAL_HA = "blink_use_local_ha"
CONF_USE_NFS = "blink_use_nfs"
# Archive name (as the panel calls it) → the option that turns it on or off.
FEATURE_OPTIONS = {"usb": CONF_USE_USB, "local_ha": CONF_USE_LOCAL_HA, "nfs": CONF_USE_NFS}
CONF_MOVE_AFTER_BACKUP = "blink_move_after_backup"
CONF_BACKUP_MINUTES = "blink_backup_minutes"
DEFAULT_BACKUP_MINUTES = 60
DEFAULT_BACKUP_STORAGE = "vistoda_archives"
MEDIA_ROOT = Path("/media")
MAX_STORAGE_DEPTH = 4
MIN_FREE_BYTES = 512 * 1024 * 1024
NETWORK_FILESYSTEMS = {"nfs", "nfs4", "cifs"}
SAFE_STORAGE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
# Local (non-network) destinations the user opted into, as exact resolved paths.
_LOCAL_DESTINATIONS: set[str] = set()
SAFE_PART = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

ARCHIVE_PROVIDERS = frozenset({PROVIDER_BLINK, PROVIDER_EZVIZ})


def storage_mount(name: str = DEFAULT_BACKUP_STORAGE) -> Path:
    """Accept a folder below /media, never an arbitrary filesystem path.

    `name` is a Supervisor media storage name, or a short `storage/sub/folder` path
    whose every part is a plain name (no dots, no empty parts, no absolute paths).
    """
    if not isinstance(name, str):
        raise ValueError("invalid network storage name")
    parts = name.split("/")
    if len(parts) > MAX_STORAGE_DEPTH or not all(SAFE_STORAGE.fullmatch(part) for part in parts):
        raise ValueError("invalid network storage name")
    return MEDIA_ROOT.joinpath(*parts)


def archive_features(options) -> dict[str, bool]:
    """Which Blink archives are in use: Blink USB, HA-local recordings, network backup."""
    return {name: bool(options.get(key, True)) for name, key in FEATURE_OPTIONS.items()}


def configured_mount(entry) -> Path:
    mount = storage_mount(entry.options.get(CONF_BACKUP_STORAGE, DEFAULT_BACKUP_STORAGE))
    allow_local_destination(mount, bool(entry.options.get(CONF_BACKUP_ALLOW_LOCAL, False)))
    return mount


def allow_local_destination(mount: Path, allowed: bool) -> None:
    """Opt a folder below /media in (or out) of being used without a network mount.

    Only exact, non-symlink folders below /media qualify, so a chosen destination can
    never point at another part of the filesystem. Network mounts keep working as before.
    """
    if allowed:
        _LOCAL_DESTINATIONS.add(str(mount))
    else:
        _LOCAL_DESTINATIONS.discard(str(mount))


def prepare_local_destination(mount: Path) -> None:
    """Create the chosen local folder (and parents) below /media with private permissions."""
    if not mount.is_relative_to(MEDIA_ROOT) or mount == MEDIA_ROOT:
        raise OSError("destination is outside /media")
    current = MEDIA_ROOT
    for part in mount.relative_to(MEDIA_ROOT).parts:
        current = current / part
        if current.is_symlink():
            raise OSError("unsafe backup directory")
        current.mkdir(exist_ok=True, mode=0o750)


def archive_entry(hass, entry_id):
    """A Blink or EZVIZ entry: the providers that copy recordings to network storage."""
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None or entry.data.get(CONF_PROVIDER) not in ARCHIVE_PROVIDERS:
        raise ValueError("invalid backup entry")
    return entry


def provider_entry(hass, provider, entry_id=""):
    if entry_id:
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is None or entry.data.get(CONF_PROVIDER) != provider:
            raise ValueError("invalid backup entry")
        return entry
    entries = [
        entry
        for entry in hass.config_entries.async_entries(DOMAIN)
        if entry.data.get(CONF_PROVIDER) == provider
    ]
    if len(entries) != 1:
        raise ValueError("ambiguous backup entry")
    return entries[0]


def network_filesystem(path: Path, *, writable: bool = True) -> str | None:
    """Require the exact mounted destination; reject local folders and symlinks.

    Writes need a read-write mount; listings and downloads also accept read-only.
    A folder the user explicitly opted into (`allow_local_destination`) is accepted as
    "local" when it is a real directory below /media.
    """
    if path.is_symlink() or path.resolve() != path:
        return None
    if str(path) in _LOCAL_DESTINATIONS and _is_local_destination(path):
        return "local"
    if not path.is_mount():
        return None
    try:
        mounts = Path("/proc/self/mounts").read_text(encoding="utf-8")
    except OSError:
        return None
    return mount_filesystem(mounts, str(path), writable=writable)


def _is_local_destination(path: Path) -> bool:
    return path.is_dir() and path.is_relative_to(MEDIA_ROOT) and path != MEDIA_ROOT


def mount_filesystem(mounts: str, path: str, *, writable: bool = True) -> str | None:
    """Network filesystem type of `path` in a /proc/self/mounts listing, else None."""
    escaped = path.replace("\\", "\\134").replace(" ", "\\040")
    for line in mounts.splitlines():
        fields = line.split()
        if (
            len(fields) >= 4
            and fields[1] == escaped
            and fields[2] in NETWORK_FILESYSTEMS
            and (not writable or "rw" in fields[3].split(","))
        ):
            return fields[2]
    return None


def storage_readiness(mount: Path, folder: Path | None = None) -> dict:
    """Return operational reasons only, without server names or mounted paths.

    `folder`, a directory inside the mount, is the one that must be writable when
    only part of the storage is (SceneTrove's share writes in device folders).
    """
    filesystem = network_filesystem(mount)
    if filesystem is None:
        return {"ready": False, "reason": "network_mount_missing"}
    inside = folder is None or (
        not folder.is_symlink() and folder.is_dir() and folder.resolve().is_relative_to(mount)
    )
    if not inside or not os.access(folder or mount, os.W_OK | os.X_OK):
        return {"ready": False, "reason": "network_mount_not_writable"}
    try:
        free = shutil.disk_usage(folder or mount).free
    except OSError:
        return {"ready": False, "reason": "network_mount_unavailable"}
    return {
        "ready": free >= MIN_FREE_BYTES,
        "reason": "ready" if free >= MIN_FREE_BYTES else "network_mount_low_space",
        "filesystem": filesystem,
    }


def safe_directory(mount: Path, *parts: str) -> Path:
    """Check each existing ancestor before creating anything beneath the mount."""
    if network_filesystem(mount) is None:
        raise OSError("network mount is absent")
    current = mount
    for part in parts:
        if not SAFE_PART.fullmatch(part):
            raise OSError("invalid backup directory")
        current = current / part
        if current.is_symlink() or not current.resolve().is_relative_to(mount):
            raise OSError("unsafe backup directory")
        current.mkdir(exist_ok=True, mode=0o750)
    return current
