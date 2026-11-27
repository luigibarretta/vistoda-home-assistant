"""Hourly verified copies of provider-owned Blink HA-local recordings."""

import asyncio

from .const import DOMAIN
from .recording_backup import (
    LOCK_KEY,
    MEDIA_EXTENSIONS,
    _backup,
    _metadata,
    _prepare,
    _source,
    _validate,
    _write_metadata,
)

PAGE_SIZE = 50
MAX_PAGES = 100
MAX_CREATED = 20


async def backup_local_recording(hass, mount, item):
    """Reuse the manual Backup NFS path; verified copies never reopen provider media."""
    recording_id = str(item.get("recording_id", ""))
    manifest = _validate(item, recording_id, MEDIA_EXTENSIONS)
    target, existing = await hass.async_add_executor_job(_prepare, "blink", manifest, mount)
    if existing:
        if target.suffix != ".mp4":
            await hass.async_add_executor_job(_write_metadata, target, _metadata("blink", manifest))
        return {"status": "existing", "relative_path": str(target.relative_to(mount))}
    manifest, upstream = await _source(hass, {"provider": "blink", "recording_id": recording_id})
    return await _backup(hass, "blink", manifest, upstream, mount)


async def local_pass(worker, runtime, mount, created):
    """Copy ready recordings in bounded pages while sharing the new-file cap per pass.

    With "move" on, a recording is deleted from the app's own archive only after its
    copy was written and its checksum verified (or an identical copy already existed).
    """
    lock = worker.hass.data.setdefault(DOMAIN, {}).setdefault(LOCK_KEY, asyncio.Lock())
    move = worker.move_enabled()
    new = checked = 0
    page = worker.local_page
    for _ in range(MAX_PAGES):
        if not worker.enabled():
            return "disabled", new, checked
        batch = await runtime.client.get_json(f"/v1/recordings?page={page}&page_size={PAGE_SIZE}")
        recordings, pagination = batch.get("recordings"), batch.get("pagination")
        if (
            not isinstance(recordings, list)
            or len(recordings) > PAGE_SIZE
            or not isinstance(pagination, dict)
        ):
            raise ValueError("invalid local recording page")
        deleted = 0
        for item in recordings:
            if not isinstance(item, dict) or item.get("status") != "ready":
                continue
            # Same lock as the manual action: both write the same target paths.
            async with lock, asyncio.timeout(180):
                result = await backup_local_recording(worker.hass, mount, item)
                if move and result["status"] in {"created", "existing"}:
                    await runtime.client.delete(f"/v1/recordings/{item['recording_id']}")
                    deleted += 1
            checked += 1
            new += result["status"] == "created"
            if created + new >= MAX_CREATED:
                worker.local_page = page
                return "pending", new, checked
        if deleted:
            # Deleting shifted the later recordings up: read the same page again.
            continue
        if not pagination.get("has_next", False):
            worker.local_page = 1
            return "complete", new, checked
        page += 1
        worker.local_page = page
    return "pending", new, checked
