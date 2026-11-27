"""Optional, bounded hourly network copies of Blink USB clips and HA-local recordings."""

import asyncio
import logging
import re
import time
from datetime import UTC, datetime, timedelta

from .backup_storage import (
    CONF_BACKUP_MINUTES,
    CONF_MOVE_AFTER_BACKUP,
    CONF_USE_LOCAL_HA,
    CONF_USE_NFS,
    CONF_USE_USB,
    DEFAULT_BACKUP_MINUTES,
    configured_mount,
    storage_readiness,
)
from .blink_local_auto_backup import MAX_CREATED, local_pass
from .blink_usb_backup import LOCK_KEY, _backup_clip
from .const import DOMAIN
from .runtime import entry_runtime

CONF_AUTO_BACKUP = "blink_usb_auto_backup"
_LOGGER = logging.getLogger(__name__)


def async_setup(hass, entry):
    """Follow current options without a Core restart; unload cancels the worker."""
    from homeassistant.helpers.event import async_track_time_interval

    worker = UsbAutoBackup(hass, entry)
    # Ticks every minute; the configured interval (1-60 minutes) decides when a pass runs.
    entry.async_on_unload(async_track_time_interval(hass, worker.tick, timedelta(minutes=1)))
    entry.async_on_unload(worker.cancel)


class UsbAutoBackup:
    def __init__(self, hass, entry):
        self.hass = hass
        self.entry = entry
        self.running = False
        self.task = None
        self.page = 1
        self.local_page = 1
        self.last_started = None

    def cancel(self):
        if self.task is not None:
            self.task.cancel()

    def due(self):
        """Whether the configured interval has passed since the last pass started."""
        if self.last_started is None:
            return True
        minutes = self.entry.options.get(CONF_BACKUP_MINUTES, DEFAULT_BACKUP_MINUTES)
        return time.monotonic() - self.last_started >= max(1, int(minutes)) * 60 - 5

    async def tick(self, _now):
        if self.running or not self.enabled() or not self.due():
            return
        self.last_started = time.monotonic()
        self.running = True
        self.task = asyncio.current_task()
        try:
            result = await self.run()
        except Exception:
            result = {"status": "unavailable"}
            _LOGGER.warning("Blink automatic network backup could not complete; will retry")
        finally:
            self.running = False
            self.task = None
        runtime = entry_runtime(self.entry)
        if runtime is not None:
            runtime.usb_backup_status = {**result, "checked_at": datetime.now(UTC).isoformat()}

    def enabled(self):
        """On only when asked for and the network backup itself is in use."""
        options = self.entry.options
        return bool(options.get(CONF_AUTO_BACKUP, False) and options.get(CONF_USE_NFS, True))

    def uses_local(self):
        return bool(self.entry.options.get(CONF_USE_LOCAL_HA, True))

    def move_enabled(self):
        """Delete a recording from the app's own archive once its copy is verified."""
        return bool(self.entry.options.get(CONF_MOVE_AFTER_BACKUP, False))

    def uses_usb(self):
        return bool(self.entry.options.get(CONF_USE_USB, True))

    async def run(self):
        """Read bounded pages and create at most 20 files per hourly pass."""
        mount = configured_mount(self.entry)
        ready = await self.hass.async_add_executor_job(storage_readiness, mount)
        if not ready["ready"]:
            return {"status": ready["reason"]}
        runtime = self.hass.data.get("blink_live_bridge", {}).get("runtime")
        if runtime is None:
            return {"status": "provider_unavailable"}
        local = ("skipped", 0, 0)
        async with asyncio.timeout(600):
            try:
                usb = await self.usb_pass(runtime) if self.uses_usb() else ("skipped", 0, 0)
            except Exception:
                # USB depends on Blink cloud; HA-local recordings must still be copied.
                usb = ("unavailable", 0, 0)
                _LOGGER.warning("Blink automatic USB backup could not complete; will retry")
            if usb[0] != "disabled" and usb[1] < MAX_CREATED and self.uses_local():
                local = await local_pass(self, runtime, mount, usb[1])
        statuses = {usb[0], local[0]}
        return {
            "status": next(
                (s for s in ("disabled", "unavailable", "pending") if s in statuses), "complete"
            ),
            "created": usb[1] + local[1],
            "checked": usb[2] + local[2],
            "local_created": local[1],
            "local_checked": local[2],
        }

    async def usb_pass(self, runtime):
        """Return (status, created, checked) for provider-owned USB clips."""
        lock = self.hass.data.setdefault(DOMAIN, {}).setdefault(LOCK_KEY, asyncio.Lock())
        created = checked = 0
        for page in range(self.page, self.page + 100):
            if not self.enabled():
                return "disabled", created, checked
            batch = await runtime.client.get_json(f"/v1/local-storage?page={page}&page_size=50")
            storages = batch.get("storages")
            if not isinstance(storages, list) or len(storages) > 16:
                raise ValueError("invalid USB inventory")
            for storage in storages:
                if (
                    not isinstance(storage.get("clips", []), list)
                    or len(storage.get("clips", [])) > 50
                ):
                    raise ValueError("invalid USB page size")
                for clip in storage.get("clips", []):
                    if not clip.get("media_available"):
                        continue
                    message = backup_message(storage, clip)
                    async with lock, asyncio.timeout(180):
                        result = await _backup_clip(self.hass, message)
                    checked += 1
                    created += result["status"] == "created"
                    if created >= MAX_CREATED:
                        self.page = page
                        return "pending", created, checked
            if not any(s.get("pagination", {}).get("has_next", False) for s in storages):
                self.page = 1
                return "complete", created, checked
            self.page = page + 1
        return "pending", created, checked


def backup_message(storage, clip):
    """Use the same stable archive layout as manual USB backup."""
    message = {key: int(storage[key]) for key in ("network_id", "sync_module_id", "manifest_id")}
    message["clip_id"] = int(clip["id"])
    if any(value <= 0 for value in message.values()):
        raise ValueError("invalid USB clip identity")
    camera = re.sub(r"[^A-Za-z0-9_-]", "_", str(clip.get("device_name") or "Telecamera_Blink"))[:64]
    return {
        **message,
        "camera": camera,
        "created_at": str(clip.get("created_at") or ""),
        "clip_length_ms": clip.get("clip_length_ms"),
    }
