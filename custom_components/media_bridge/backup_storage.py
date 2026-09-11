"""Validated Home Assistant network-storage configuration and redacted readiness."""

import os
import re
import shutil
from pathlib import Path

from .const import CONF_PROVIDER, DOMAIN

CONF_BACKUP_STORAGE = "backup_storage"
DEFAULT_BACKUP_STORAGE = "vistoda_archives"
MIN_FREE_BYTES = 512 * 1024 * 1024
NETWORK_FILESYSTEMS = {"nfs", "nfs4", "cifs"}
SAFE_STORAGE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
SAFE_PART = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def storage_mount(name: str = DEFAULT_BACKUP_STORAGE) -> Path:
    """Accept a Supervisor media storage name, never an arbitrary filesystem path."""
    if not isinstance(name, str) or not SAFE_STORAGE.fullmatch(name):
        raise ValueError("invalid network storage name")
    return Path("/media") / name


def configured_mount(entry) -> Path:
    return storage_mount(entry.options.get(CONF_BACKUP_STORAGE, DEFAULT_BACKUP_STORAGE))


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


def network_filesystem(path: Path) -> str | None:
    """Require the exact mounted destination; reject local folders and symlinks."""
    if path.is_symlink() or path.resolve() != path or not path.is_mount():
        return None
    escaped = str(path).replace("\\", "\\134").replace(" ", "\\040")
    try:
        mounts = Path("/proc/self/mounts").read_text(encoding="utf-8")
    except OSError:
        return None
    for line in mounts.splitlines():
        fields = line.split()
        if (
            len(fields) >= 4
            and fields[1] == escaped
            and fields[2] in NETWORK_FILESYSTEMS
            and "rw" in fields[3].split(",")
        ):
            return fields[2]
    return None


def storage_readiness(mount: Path) -> dict:
    """Return operational reasons only, without server names or mounted paths."""
    filesystem = network_filesystem(mount)
    if filesystem is None:
        return {"ready": False, "reason": "network_mount_missing"}
    if not os.access(mount, os.W_OK | os.X_OK):
        return {"ready": False, "reason": "network_mount_not_writable"}
    try:
        free = shutil.disk_usage(mount).free
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
