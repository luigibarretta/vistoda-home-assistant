"""Move ready microSD clips of a shared EZVIZ entry into SceneTrove's device folder.

Each clip is copied with the network backup's checks (size and SHA-256 against
the bridge manifest, fsync, atomic rename, sidecar) under the name SceneTrove
indexes; only then is the bridge copy deleted, so /data keeps no duplicate.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import timedelta

from aiohttp import ClientError

from .backup_storage import safe_directory, storage_mount
from .const import CONF_ALIAS, CONF_SCENETROVE_DEVICE, CONF_SHARED_STORAGE, PROVIDER_EZVIZ
from .errors import BridgeError
from .network_archive import verified
from .recording_backup import _backup, _ensure_metadata, _metadata, _prepare, _validate
from .shared_archive import shared_clip_name, sharing

_LOGGER = logging.getLogger(__name__)
INTERVAL = timedelta(seconds=60)
RETRY_AFTER_SECONDS = 1800
MAX_PAGES = 10
# One move at a time across entries and reloads: a copy is never raced.
_MOVING = asyncio.Lock()


class SharedClipMover:
    """Polls the bridge while the entry shares its archive with SceneTrove."""

    def __init__(self, hass, entry, client) -> None:
        self.hass, self.entry, self.client = hass, entry, client
        self._retry_at: dict[str, float] = {}

    def start(self) -> None:
        from homeassistant.core import callback
        from homeassistant.helpers.event import async_track_time_interval

        @callback
        def tick(_now) -> None:
            # An entry task: unloading the entry cancels a move in progress.
            self.entry.async_create_background_task(self.hass, self.run(), "vistoda_shared_clips")

        self.entry.async_on_unload(async_track_time_interval(self.hass, tick, INTERVAL))

    async def run(self, _now=None) -> None:
        """Move every ready microSD clip of this camera; others stay on the bridge."""
        if not sharing(self.entry) or _MOVING.locked():
            return
        async with _MOVING:
            alias = self.entry.data[CONF_ALIAS]
            for page in range(1, MAX_PAGES + 1):
                try:
                    listed = await self.client.provider_recordings(page, 100, camera=alias)
                except BridgeError:
                    return
                for recording in listed["recordings"]:
                    if recording["status"] == "ready" and shared_clip_name(recording):
                        await self._move(recording["recording_id"], alias)
                if not listed.get("pagination", {}).get("has_next"):
                    return

    async def _move(self, recording_id: str, alias: str) -> None:
        if self._retry_at.get(recording_id, 0) > time.monotonic():
            return
        try:
            manifest = _validate(
                await self.client.provider_recording(recording_id), recording_id, "video/mpeg"
            )
            name = shared_clip_name(manifest)
            if manifest["camera"] != alias or name is None:
                return
            mount = storage_mount(self.entry.options[CONF_SHARED_STORAGE])
            device = self.entry.options.get(CONF_SCENETROVE_DEVICE) or alias
            folder = await self.hass.async_add_executor_job(safe_directory, mount, device)
            target, existing = await self.hass.async_add_executor_job(
                _prepare, PROVIDER_EZVIZ, manifest, mount, folder / name
            )
            if existing:
                metadata = _metadata(PROVIDER_EZVIZ, manifest)
                await self.hass.async_add_executor_job(_ensure_metadata, target, metadata)
            else:
                upstream = await self.client.open_provider_recording(recording_id)
                await _backup(self.hass, PROVIDER_EZVIZ, manifest, upstream, mount, target)
            # The shared copy is checked again right before the bridge copy goes.
            await self.hass.async_add_executor_job(
                lambda: verified(target, manifest, checksum=True)
            )
            await self.client.delete_provider_recording(recording_id)
        except (BridgeError, ClientError, TimeoutError, OSError, ValueError) as error:
            # The bridge copy stays; this clip is retried later.
            self._retry_at[recording_id] = time.monotonic() + RETRY_AFTER_SECONDS
            _LOGGER.warning("Could not share EZVIZ clip %s: %s", recording_id, type(error).__name__)
