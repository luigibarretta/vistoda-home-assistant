"""Persistent custom lists shared by each Vistoda video provider."""

import asyncio
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .recording_list_model import RecordingListData

STORAGE_KEY = f"{DOMAIN}.provider_recording_lists"
STORAGE_VERSION = 1
DATA_KEY = "_provider_recording_lists"


class ProviderRecordingLists:
    """Serialize provider-list mutations in Home Assistant private storage."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, STORAGE_KEY, private=True, atomic_writes=True
        )
        self._model: RecordingListData | None = None
        self._lock = asyncio.Lock()

    async def async_snapshot(self, scope: str) -> list[dict]:
        async with self._lock:
            model = await self._async_model()
            lists, changed = model.snapshot(scope)
            if changed:
                await self._store.async_save(model.data)
            return lists

    async def async_create(self, scope: str, name: str) -> tuple[list[dict], str]:
        async with self._lock:
            model = await self._async_model()
            lists, list_id = model.create(scope, name)
            await self._store.async_save(model.data)
            return lists, list_id

    async def async_update(self, scope: str, list_id: str, name: str) -> list[dict]:
        async with self._lock:
            model = await self._async_model()
            lists, changed = model.update(scope, list_id, name)
            if changed:
                await self._store.async_save(model.data)
            return lists

    async def async_delete(self, scope: str, list_id: str) -> tuple[list[dict], bool]:
        async with self._lock:
            model = await self._async_model()
            lists, changed = model.delete(scope, list_id)
            if changed:
                await self._store.async_save(model.data)
            return lists, changed

    async def async_set_membership(
        self, scope: str, list_id: str, recording_id: str, included: bool
    ) -> list[dict]:
        async with self._lock:
            model = await self._async_model()
            lists, changed = model.set_membership(scope, list_id, recording_id, included)
            if changed:
                await self._store.async_save(model.data)
            return lists

    async def _async_model(self) -> RecordingListData:
        if self._model is None:
            self._model = RecordingListData(await self._store.async_load())
        return self._model


def async_get_provider_recording_lists(hass: HomeAssistant) -> ProviderRecordingLists:
    data = hass.data.setdefault(DOMAIN, {})
    if DATA_KEY not in data:
        data[DATA_KEY] = ProviderRecordingLists(hass)
    return data[DATA_KEY]
