"""Archive EZVIZ alarms on the Vistoda network storage (opt-in per entry).

Live alarms come from the listener's dispatcher signal. A backfill walks the
whole app history window (newest first, `before` pages) and archives what is
missing, at start, when the listener reconnects and when the option is turned
on, so outages and late opt-ins leave no gaps. Writes are serialized and run in
the executor; a missing mount is reported once per outage and never stops
alarms from reaching Home Assistant.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import timedelta
from typing import Any

from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect, async_dispatcher_send

from .backup_storage import configured_mount
from .const import (
    CONF_EVENT_ARCHIVE,
    CONF_EVENT_RETENTION_DAYS,
    ezviz_alarm_signal,
    ezviz_event_archive_signal,
)
from .errors import BridgeError
from .event_archive import SAFE_ID, has_event, prune_events, write_event

_LOGGER = logging.getLogger(__name__)
PROVIDER = "ezviz"
DAY = timedelta(days=1)


class EzvizEventArchiver:
    def __init__(self, hass, entry, client, alias: str) -> None:
        self.hass = hass
        self.entry = entry
        self.client = client
        self.alias = alias
        self.unavailable = False
        self._writing = asyncio.Lock()
        self._backfilling = asyncio.Lock()

    @property
    def enabled(self) -> bool:
        return bool(self.entry.options.get(CONF_EVENT_ARCHIVE, False))

    def start(self) -> None:
        """Follow live alarms, backfill and prune daily; options are read live."""
        from homeassistant.helpers.event import async_track_time_interval

        signal = ezviz_alarm_signal(self.entry.entry_id)
        self.entry.async_on_unload(async_dispatcher_connect(self.hass, signal, self._on_alarm))
        self.entry.async_on_unload(async_track_time_interval(self.hass, self.prune, DAY))
        self.entry.async_on_unload(self.entry.add_update_listener(self._options_updated))
        self._schedule_backfill()

    @callback
    def _on_alarm(self, data: dict[str, Any] | None) -> None:
        if not self.enabled:
            return
        if data is None:  # the listener's connection state changed
            self._schedule_backfill()
            return
        self.entry.async_create_background_task(
            self.hass, self.archive(data), f"Vistoda EZVIZ event archive {data['alarm_id']}"
        )

    @callback
    def _schedule_backfill(self) -> None:
        self.entry.async_create_background_task(
            self.hass, self.backfill(), f"Vistoda EZVIZ event backfill {self.entry.entry_id}"
        )

    async def _options_updated(self, _hass, _entry) -> None:
        # Update listeners run outside the entry's task tracking: hand over.
        self._schedule_backfill()

    async def archive(self, data: dict[str, Any]) -> None:
        """Archive one published alarm with its picture when it has one."""
        if self.enabled and _archivable(data["alarm_id"]):
            jpeg = await self._picture(data["alarm_id"]) if data.get("picture") else None
            await self._write(data, jpeg)

    async def backfill(self) -> None:
        """Archive every alarm of the app history window that is not archived yet."""
        if not self.enabled or self._backfilling.locked():
            return
        async with self._backfilling:
            await self._walk_history()
        await self.prune()

    async def _walk_history(self) -> None:
        before = None
        while True:
            try:
                batch = await (
                    self.client.ezviz_alarms(self.alias)
                    if before is None
                    else self.client.ezviz_alarms(self.alias, before=before)
                )
            except BridgeError:
                return
            for alarm in sorted(batch.events, key=lambda event: event.occurred_at, reverse=True):
                if not _archivable(alarm.alarm_id):
                    continue
                archived = await self._archived(alarm)
                if archived is None:  # mount unavailable: retry on the next trigger
                    return
                if not archived:
                    jpeg = await self._picture(alarm.alarm_id) if alarm.picture_available else None
                    if await self._write(_record(alarm), jpeg) is None:
                        return
            if batch.older is None:
                return
            before = batch.older

    async def prune(self, _now=None) -> None:
        """Delete archived events older than the configured retention."""
        days = int(self.entry.options.get(CONF_EVENT_RETENTION_DAYS, 0))
        if not self.enabled or days <= 0:
            return
        older_than = int(time.time()) - days * 86_400
        try:
            removed = await self.hass.async_add_executor_job(
                lambda: prune_events(
                    configured_mount(self.entry), PROVIDER, self.alias, older_than=older_than
                )
            )
        except (OSError, ValueError):
            self._report_unavailable()
            return
        if removed:
            _LOGGER.info("Removed %s archived EZVIZ events past retention", removed)

    async def _picture(self, alarm_id: str) -> bytes | None:
        try:
            return await self.client.ezviz_alarm_picture(self.alias, alarm_id)
        except BridgeError:
            return None

    async def _archived(self, alarm) -> bool | None:
        try:
            return await self.hass.async_add_executor_job(
                has_event,
                configured_mount(self.entry),
                PROVIDER,
                self.alias,
                alarm.occurred_at,
                alarm.alarm_id,
            )
        except (OSError, ValueError):
            self._report_unavailable()
            return None

    async def _write(self, alarm: dict[str, Any], jpeg: bytes | None) -> bool | None:
        try:
            async with self._writing:
                written = await self.hass.async_add_executor_job(
                    write_event, configured_mount(self.entry), PROVIDER, self.alias, alarm, jpeg
                )
        except (OSError, ValueError):
            self._report_unavailable()
            return None
        if self.unavailable:
            _LOGGER.info("EZVIZ event archive is available again")
            self._set_unavailable(False)
        return written

    def _report_unavailable(self) -> None:
        if not self.unavailable:
            _LOGGER.warning("EZVIZ event archive is unavailable; check the network storage")
            self._set_unavailable(True)

    def _set_unavailable(self, value: bool) -> None:
        self.unavailable = value
        async_dispatcher_send(self.hass, ezviz_event_archive_signal(self.entry.entry_id))


def _record(alarm) -> dict[str, Any]:
    return {
        "alarm_id": alarm.alarm_id,
        "occurred_at": alarm.occurred_at,
        "category": alarm.category,
        "alarm_type": alarm.alarm_type,
        "title": alarm.title,
    }


def _archivable(alarm_id: str) -> bool:
    """Vendor ids outside the archive's name rules are skipped, not an outage."""
    if SAFE_ID.fullmatch(alarm_id):
        return True
    _LOGGER.debug("Skipping an EZVIZ alarm whose id cannot name an archive file")
    return False
