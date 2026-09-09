"""Home Assistant Store wrapper for Ring recording lists."""

import asyncio
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .recording_list_model import RecordingListData

STORAGE_KEY = f"{DOMAIN}.ring_recording_lists"
STORAGE_VERSION = 1
DATA_KEY = "_ring_recording_lists"


class RingRecordingLists:
    """Serialize list mutations and persist them privately."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, STORAGE_KEY, private=True, atomic_writes=True
        )
        self._model: RecordingListData | None = None
        self._lock = asyncio.Lock()

    async def async_snapshot(
        self, entry_id: str, valid_recording_ids: set[str] | None = None
    ) -> list[dict]:
        """Return lists and reconcile stale recording IDs."""
        async with self._lock:
            model = await self._async_model()
            lists, changed = model.snapshot(entry_id, valid_recording_ids)
            if changed:
                await self._store.async_save(model.data)
            return lists

    async def async_create(self, entry_id: str, name: str) -> tuple[list[dict], str]:
        """Create and persist one list."""
        async with self._lock:
            model = await self._async_model()
            lists, list_id = model.create(entry_id, name)
            await self._store.async_save(model.data)
            return lists, list_id

    async def async_delete(self, entry_id: str, list_id: str) -> tuple[list[dict], bool]:
        """Delete and persist one list."""
        async with self._lock:
            model = await self._async_model()
            lists, changed = model.delete(entry_id, list_id)
            if changed:
                await self._store.async_save(model.data)
            return lists, changed

    async def async_update(self, entry_id: str, list_id: str, name: str) -> list[dict]:
        """Rename and persist one list."""
        async with self._lock:
            model = await self._async_model()
            lists, changed = model.update(entry_id, list_id, name)
            if changed:
                await self._store.async_save(model.data)
            return lists

    async def async_set_membership(
        self, entry_id: str, list_id: str, recording_id: str, included: bool
    ) -> list[dict]:
        """Persist one membership change."""
        async with self._lock:
            model = await self._async_model()
            lists, changed = model.set_membership(entry_id, list_id, recording_id, included)
            if changed:
                await self._store.async_save(model.data)
            return lists

    async def async_remove_recordings(self, entry_id: str, recording_ids: set[str]) -> None:
        """Forget deleted media from all lists."""
        if not recording_ids:
            return
        async with self._lock:
            model = await self._async_model()
            if model.remove_recordings(entry_id, recording_ids):
                await self._store.async_save(model.data)

    async def _async_model(self) -> RecordingListData:
        if self._model is None:
            self._model = RecordingListData(await self._store.async_load())
        return self._model


def async_get_recording_lists(hass: HomeAssistant) -> RingRecordingLists:
    """Return the integration-owned singleton store."""
    data = hass.data.setdefault(DOMAIN, {})
    if DATA_KEY not in data:
        data[DATA_KEY] = RingRecordingLists(hass)
    return data[DATA_KEY]
