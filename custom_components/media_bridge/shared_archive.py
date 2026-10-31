"""SceneTrove's device folder on network storage, shared with Vistoda.

In the shared clip destination Vistoda writes a camera's microSD clips and
events once into that folder, named as SceneTrove indexes its own files.
"""

import re
from datetime import UTC, datetime

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
