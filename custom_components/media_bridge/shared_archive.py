"""SceneTrove's device folder on network storage, shared with Vistoda.

In the shared clip destination Vistoda writes a camera's microSD clips and
events once into that folder, named as SceneTrove indexes its own files.
"""

import re
from datetime import UTC, datetime

from .backup_storage import configured_mount, storage_mount
from .const import (
    CONF_ALIAS,
    CONF_CLIP_DESTINATION,
    CONF_SCENETROVE_DEVICE,
    CONF_SCENETROVE_URL,
    CONF_SHARED_STORAGE,
    PROVIDER_EZVIZ,
)
from .event_folder import EventFolder, shared_folder, vistoda_folder

# SceneTrove indexes only lowercase UUID clip ids.
CLIP_ID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


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


def sharing(entry) -> bool:
    """Whether the entry writes its clips and events into SceneTrove's folder."""
    return entry.options.get(CONF_CLIP_DESTINATION) == "shared" and bool(
        entry.options.get(CONF_SCENETROVE_URL) and entry.options.get(CONF_SHARED_STORAGE)
    )


def event_folders(entry) -> tuple[EventFolder, ...]:
    """The entry's event folders, the one its current mode writes first.

    Both are read once a shared storage is set, so switching modes moves no
    file and hides none.
    """
    alias = entry.data[CONF_ALIAS]
    vistoda = vistoda_folder(configured_mount(entry), PROVIDER_EZVIZ, alias)
    storage = entry.options.get(CONF_SHARED_STORAGE)
    if not storage:
        return (vistoda,)
    device = entry.options.get(CONF_SCENETROVE_DEVICE) or alias
    shared = shared_folder(storage_mount(storage), device, PROVIDER_EZVIZ, alias)
    return (shared, vistoda) if sharing(entry) else (vistoda, shared)
