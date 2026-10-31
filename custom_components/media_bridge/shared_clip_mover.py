"""Move ready microSD clips of a shared EZVIZ entry into SceneTrove's device folder.

Each clip is copied with the network backup's checks (size and SHA-256 against
the bridge manifest, fsync, atomic rename, sidecar) under the name SceneTrove
indexes; only then is the bridge copy deleted, so /data keeps no duplicate.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from .backup_storage import safe_directory, storage_mount
from .const import CONF_ALIAS, CONF_SCENETROVE_DEVICE, CONF_SHARED_STORAGE, PROVIDER_EZVIZ
from .errors import BridgeError
from .recording_backup import _backup, _validate
from .shared_archive import shared_clip_name, sharing

_LOGGER = logging.getLogger(__name__)
INTERVAL = timedelta(seconds=60)


class SharedClipMover:
    """Polls the bridge while the entry shares its archive with SceneTrove."""

    def __init__(self, hass, entry, client) -> None:
        self.hass, self.entry, self.client = hass, entry, client
        self._running = asyncio.Lock()

    def start(self) -> None:
        from homeassistant.helpers.event import async_track_time_interval

        self.entry.async_on_unload(async_track_time_interval(self.hass, self.run, INTERVAL))

    async def run(self, _now=None) -> None:
        """Move every ready microSD clip of this camera; others stay on the bridge."""
        if not sharing(self.entry) or self._running.locked():
            return
        async with self._running:
            alias = self.entry.data[CONF_ALIAS]
            try:
                page = await self.client.provider_recordings(1, 100, camera=alias)
            except BridgeError:
                return
            for recording in page["recordings"]:
                if recording["status"] == "ready" and shared_clip_name(recording):
                    await self._move(recording["recording_id"], alias)

    async def _move(self, recording_id: str, alias: str) -> None:
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
            upstream = await self.client.open_provider_recording(recording_id)
            await _backup(self.hass, PROVIDER_EZVIZ, manifest, upstream, mount, folder / name)
            await self.client.delete_provider_recording(recording_id)
        except (BridgeError, OSError, ValueError) as error:
            # The bridge copy stays; the next run retries.
            _LOGGER.warning("Could not share EZVIZ clip %s: %s", recording_id, type(error).__name__)
