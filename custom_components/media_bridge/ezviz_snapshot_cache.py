"""Private persistent cache for manually requested EZVIZ snapshots."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

MAX_SNAPSHOT_BYTES = 12 * 1024 * 1024


def _paths(hass: HomeAssistant, entry_id: str) -> tuple[Path, Path]:
    base = Path(hass.config.path(".storage", f"media_bridge_ezviz_{entry_id}"))
    return base.with_suffix(".jpg"), base.with_suffix(".json")


async def async_load(hass: HomeAssistant, entry_id: str) -> tuple[bytes | None, str | None]:
    """Load only a complete bounded JPEG and its owned timestamp."""
    return await hass.async_add_executor_job(_load, *_paths(hass, entry_id))


def _load(image_path: Path, metadata_path: Path) -> tuple[bytes | None, str | None]:
    try:
        image = image_path.read_bytes()
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None, None
    if not 4 <= len(image) <= MAX_SNAPSHOT_BYTES or not (
        image.startswith(b"\xff\xd8") and image.endswith(b"\xff\xd9")
    ):
        return None, None
    updated_at = metadata.get("updated_at") if isinstance(metadata, dict) else None
    return image, updated_at if isinstance(updated_at, str) else None


async def async_save(hass: HomeAssistant, entry_id: str, image: bytes) -> str:
    """Atomically retain the last explicitly requested snapshot."""
    if not 4 <= len(image) <= MAX_SNAPSHOT_BYTES or not (
        image.startswith(b"\xff\xd8") and image.endswith(b"\xff\xd9")
    ):
        raise ValueError("snapshot is not a complete bounded JPEG")
    updated_at = datetime.now(UTC).isoformat()
    await hass.async_add_executor_job(_save, *_paths(hass, entry_id), image, updated_at)
    return updated_at


def _save(image_path: Path, metadata_path: Path, image: bytes, updated_at: str) -> None:
    image_path.parent.mkdir(parents=True, exist_ok=True)
    image_tmp = image_path.with_suffix(".jpg.tmp")
    metadata_tmp = metadata_path.with_suffix(".json.tmp")
    with image_tmp.open("wb") as stream:
        stream.write(image)
        stream.flush()
        os.fsync(stream.fileno())
    with metadata_tmp.open("w", encoding="utf-8") as stream:
        json.dump({"schema_version": 1, "updated_at": updated_at}, stream)
        stream.flush()
        os.fsync(stream.fileno())
    image_tmp.replace(image_path)
    metadata_tmp.replace(metadata_path)
