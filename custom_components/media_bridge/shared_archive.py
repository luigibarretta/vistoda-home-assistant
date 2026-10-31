"""SceneTrove's device folder on network storage, shared with Vistoda.

In the shared clip destination Vistoda writes a camera's microSD clips and
events once into that folder, named as SceneTrove indexes its own files.
"""

import json
import re
from datetime import UTC, datetime
from pathlib import Path

from .backup_storage import SAFE_PART, configured_mount, network_filesystem, storage_mount
from .const import (
    CONF_ALIAS,
    CONF_CLIP_DESTINATION,
    CONF_SCENETROVE_DEVICE,
    CONF_SCENETROVE_URL,
    CONF_SHARED_STORAGE,
    PROVIDER_EZVIZ,
)
from .event_folder import EventFolder, shared_folder, vistoda_folder
from .network_archive import MAX_ITEMS, recording_span, verified

# SceneTrove indexes only lowercase UUID clip ids.
CLIP_ID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
SHARED_NAME = re.compile(r"hiv\d{8}T\d{6}Z-[0-9a-f-]{36}\.mpegps")
# Archive ids of shared clips, next to the `ezviz/<camera>/…` network copies.
SHARED_PREFIX = "shared/"


def shared_clip_name(recording: dict) -> str | None:
    """`hiv<microSD start, UTC>Z-<id>.mpegps`, or None for clips SceneTrove cannot play."""
    if (
        recording.get("media_type") != "video/mpeg"
        or recording.get("source") != "sd"
        or not isinstance(recording.get("sd_start"), int)
        or not CLIP_ID.fullmatch(str(recording.get("recording_id", "")))
    ):
        return None
    stamp = datetime.fromtimestamp(recording["sd_start"], UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"hiv{stamp}-{recording['recording_id']}.mpegps"


def shared_mount(entry) -> Path | None:
    """The network storage holding SceneTrove's device folders, when validly set."""
    try:
        return storage_mount(entry.options[CONF_SHARED_STORAGE])
    except (KeyError, ValueError):
        return None


def sharing(entry) -> bool:
    """Whether the entry writes its clips and events into SceneTrove's folder."""
    return (
        entry.options.get(CONF_CLIP_DESTINATION) == "shared"
        and bool(entry.options.get(CONF_SCENETROVE_URL))
        and shared_mount(entry) is not None
    )


def event_folders(entry) -> tuple[EventFolder, ...]:
    """The entry's event folders, the one its current mode writes first.

    Both are read once a shared storage is set, so switching modes moves no
    file and hides none.
    """
    alias = entry.data[CONF_ALIAS]
    vistoda = vistoda_folder(configured_mount(entry), PROVIDER_EZVIZ, alias)
    mount = shared_mount(entry)
    if mount is None:
        return (vistoda,)
    device = entry.options.get(CONF_SCENETROVE_DEVICE) or alias
    shared = shared_folder(mount, device, PROVIDER_EZVIZ, alias)
    return (shared, vistoda) if sharing(entry) else (vistoda, shared)


def shared_clip(
    mount: Path, device: str, alias: str, item_id: str, *, checksum: bool = False
) -> tuple[Path, dict]:
    """Checked path and archive item of a clip Vistoda shared; ValueError otherwise.

    Only clips with Vistoda's sidecar qualify: SceneTrove's own files are never
    listed or deleted from here.
    """
    name = item_id.removeprefix(SHARED_PREFIX)
    if not (
        item_id.startswith(SHARED_PREFIX)
        and SHARED_NAME.fullmatch(name)
        and SAFE_PART.fullmatch(device)
        and network_filesystem(mount, writable=False)
    ):
        raise ValueError("not a shared clip")
    target = mount / device / name
    sidecar = target.with_name(f"{name}.json")
    if any(path.is_symlink() for path in (target.parent, target, sidecar)):
        raise ValueError("unsafe shared clip")
    if sidecar.stat().st_size > 16384:
        raise ValueError("unsafe shared clip metadata")
    metadata = json.loads(sidecar.read_text(encoding="utf-8"))
    recording = metadata.get("recording")
    if (
        metadata.get("schema_version") != 1
        or metadata.get("provider") != PROVIDER_EZVIZ
        or not isinstance(recording, dict)
        or recording.get("camera") != alias
        or shared_clip_name(recording) != name
    ):
        raise ValueError("shared clip identity mismatch")
    size = verified(target, recording, checksum=checksum)
    return target, {
        "id": item_id,
        "media_id": f"local:{recording['recording_id']}",
        "camera": alias,
        "created_at": recording.get("requested_at", ""),
        "backed_up_at": metadata.get("backed_up_at", ""),
        "bytes": size,
        "media_type": "video/mpeg",
        "span": recording_span(recording),
        "shared": True,
    }


def shared_inventory(mount: Path, device: str, alias: str) -> list[dict]:
    """The clips this camera shared in SceneTrove's device folder."""
    folder = mount / device
    if not SAFE_PART.fullmatch(device) or folder.is_symlink() or not folder.is_dir():
        return []
    items = []
    for sidecar in sorted(folder.glob("hiv*.mpegps.json"))[:MAX_ITEMS]:
        try:
            items.append(shared_clip(mount, device, alias, SHARED_PREFIX + sidecar.name[:-5])[1])
        except (ValueError, OSError, TypeError, KeyError):
            continue
    return items


def delete_shared_clip(mount: Path, device: str, alias: str, item_id: str) -> bool:
    """Delete a shared clip and its sidecar; SceneTrove loses it too. False when refused."""
    try:
        target, _item = shared_clip(mount, device, alias, item_id)
    except (ValueError, OSError, TypeError, KeyError):
        return False
    target.unlink()
    target.with_name(f"{target.name}.json").unlink(missing_ok=True)
    return True
