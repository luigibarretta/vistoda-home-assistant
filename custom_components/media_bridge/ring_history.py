"""Persistent Ring event overlay and exactly-once unlock publication."""

import asyncio
import time
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .client_ring_history import RingHistoryPage
from .const import DOMAIN
from .errors import BridgeError
from .ring_history_model import sources_overlap, unlock_message
from .ring_identity import (
    configuration_payload,
    home_assistant_identity,
    normalize_settings,
    resolve_identity,
    validate_update,
)

EVENT_RING_UNLOCKED = "vistoda_ring_entry_unlocked"
HISTORY_TYPES = {"unlock", "live_view", "ding", "motion", "activity"}
MAX_LOCAL_EVENTS = 64
MAX_LOCAL_OVERLAY = 10
DEDUPE_SECONDS = 12


class RingHistoryManager:
    """Merge cloud history with locally observed actions and deduplicate unlocks."""

    def __init__(self, hass, entry, client, alias: str) -> None:
        self.hass = hass
        self.entry = entry
        self.client = client
        self.alias = alias
        self._store: Store[dict[str, Any]] = Store(
            hass,
            1,
            f"{DOMAIN}.ring_history.{entry.entry_id}",
            private=True,
            atomic_writes=True,
        )
        self._data: dict[str, Any] | None = None
        self._lock = asyncio.Lock()

    @property
    def identity(self) -> dict[str, str]:
        """Return the effective identity selected by the user."""
        data = self._data or {}
        raw = data.get("identity") if isinstance(data.get("identity"), dict) else {}
        provider = {
            "device_name": _safe_name(raw.get("device_name"), self.alias),
            "location_name": _safe_name(raw.get("location_name"), "Ring"),
            "city": _safe_name(raw.get("city"), ""),
        }
        return resolve_identity(
            provider,
            home_assistant_identity(self.hass, self.entry, self.alias),
            data.get("identity_settings"),
        )

    @property
    def identity_configuration(self) -> dict[str, Any]:
        """Return safe values and current source selection for the editor."""
        data = self._data or {}
        raw = data.get("identity") if isinstance(data.get("identity"), dict) else {}
        provider = {
            "device_name": _safe_name(raw.get("device_name"), self.alias),
            "location_name": _safe_name(raw.get("location_name"), "Ring"),
            "city": _safe_name(raw.get("city"), ""),
        }
        return configuration_payload(
            provider,
            home_assistant_identity(self.hass, self.entry, self.alias),
            data.get("identity_settings"),
        )

    async def async_initialize(self) -> None:
        """Load persisted history without blocking entry setup on Ring cloud."""
        await self._async_load()

    async def async_warm_provider(self) -> None:
        """Refresh provider identity in an entry-owned background task."""
        await self.async_page(1, None)

    async def async_page(self, limit: int, cursor: str | None) -> dict[str, Any]:
        """Return one provider page with a small, non-lossy first-page overlay."""
        await self._async_load()
        provider: RingHistoryPage | None = None
        try:
            provider = await self.client.ring_history(self.alias, limit, cursor)
        except BridgeError:
            if cursor is not None:
                return self._result([], None, True)
        async with self._lock:
            if provider is not None:
                identity = {
                    "device_name": provider.identity.device_name,
                    "location_name": provider.identity.location_name,
                    "city": provider.identity.city or "",
                }
                if self._data.get("identity") != identity:
                    self._data["identity"] = identity
                    await self._store.async_save(self._data)
            cloud = [] if provider is None else [_event_dict(item) for item in provider.events]
            events = cloud
            if cursor is None:
                local = [item for item in self._data["events"] if _valid_event(item)]
                overlay = [
                    item
                    for item in local
                    if not any(_same_activity(item, remote) for remote in cloud)
                ][:MAX_LOCAL_OVERLAY]
                events = sorted(
                    [*cloud, *overlay], key=lambda item: item["occurred_at"], reverse=True
                )
            next_cursor = provider.next_cursor if provider is not None else None
            return self._result(events, next_cursor, provider is None)

    async def async_record(self, event_type: str, occurred_at: int | None, source: str) -> bool:
        """Persist one observed event and publish a unique unlock notification event."""
        if event_type not in HISTORY_TYPES:
            return False
        timestamp = int(occurred_at or time.time())
        await self._async_load()
        async with self._lock:
            recent = next(
                (
                    item
                    for item in self._data["events"]
                    if _valid_event(item)
                    and item["event_type"] == event_type
                    and abs(item["occurred_at"] - timestamp) <= DEDUPE_SECONDS
                ),
                None,
            )
            if recent is not None and sources_overlap(recent.get("source", ""), source):
                return False
            item = {
                "event_id": f"local-{uuid4()}",
                "event_type": event_type,
                "occurred_at": timestamp,
                "source": source,
            }
            self._data["events"] = sorted(
                [item, *[entry for entry in self._data["events"] if _valid_event(entry)]],
                key=lambda entry: entry["occurred_at"],
                reverse=True,
            )[:MAX_LOCAL_EVENTS]
            await self._store.async_save(self._data)
        if event_type == "unlock":
            self._publish_unlock(timestamp, source)
        return True

    async def async_update_identity(
        self, selection: dict[str, str], custom: dict[str, str]
    ) -> dict[str, Any]:
        """Persist user-controlled identity sources and return the effective view."""
        settings = validate_update(selection, custom)
        await self._async_load()
        async with self._lock:
            self._data["identity_settings"] = settings
            await self._store.async_save(self._data)
        return {
            "identity": self.identity,
            "identity_configuration": self.identity_configuration,
        }

    async def _async_load(self) -> None:
        if self._data is not None:
            return
        async with self._lock:
            if self._data is not None:
                return
            loaded = await self._store.async_load()
            self._data = loaded if isinstance(loaded, dict) else {}
            if not isinstance(self._data.get("events"), list):
                self._data["events"] = []
            self._data["identity_settings"] = normalize_settings(
                self._data.get("identity_settings")
            )

    def _result(self, events, next_cursor, degraded: bool) -> dict[str, Any]:
        return {
            "identity": self.identity,
            "identity_configuration": self.identity_configuration,
            "events": [
                {key: item[key] for key in ("event_id", "event_type", "occurred_at")}
                for item in events
            ],
            "next_cursor": next_cursor,
            "degraded": degraded,
        }

    def _publish_unlock(self, occurred_at: int, source: str) -> None:
        identity = self.identity
        local = dt_util.as_local(datetime.fromtimestamp(occurred_at, UTC))
        message = unlock_message(identity, local)
        self.hass.bus.async_fire(
            EVENT_RING_UNLOCKED,
            {
                **identity,
                "entry_id": self.entry.entry_id,
                "alias": self.alias,
                "occurred_at": occurred_at,
                "source": source,
                "message": message,
            },
        )


def _event_dict(item) -> dict[str, Any]:
    return {
        "event_id": item.event_id,
        "event_type": item.event_type,
        "occurred_at": item.occurred_at,
    }


def _safe_name(value, fallback: str) -> str:
    return (
        value
        if isinstance(value, str) and value and len(value) <= 128 and value.isprintable()
        else fallback
    )


def _valid_event(item) -> bool:
    return (
        isinstance(item, dict)
        and isinstance(item.get("event_id"), str)
        and 0 < len(item["event_id"]) <= 128
        and item["event_id"].isprintable()
        and item.get("event_type") in HISTORY_TYPES
        and isinstance(item.get("occurred_at"), int)
        and item["occurred_at"] >= 0
    )


def _same_activity(left, right) -> bool:
    return (
        left["event_type"] == right["event_type"]
        and abs(left["occurred_at"] - right["occurred_at"]) <= DEDUPE_SECONDS
    )
