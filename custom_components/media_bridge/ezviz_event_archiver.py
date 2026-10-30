"""Archive EZVIZ alarms on the Vistoda network storage (opt-in per entry).

Live alarms come from the listener's dispatcher signal; at start a backfill
walks the app history newest first with `before` until it meets an alarm that
is already archived. Filesystem work runs in the executor; a missing mount is
reported once per outage and never stops alarms from reaching Home Assistant.
"""

from __future__ import annotations

import logging
import time
from datetime import timedelta
from typing import Any

from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .backup_storage import configured_mount
from .const import CONF_EVENT_ARCHIVE, CONF_EVENT_RETENTION_DAYS, ezviz_alarm_signal
from .errors import BridgeError
from .event_archive import prune_events, write_event

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

    @property
    def enabled(self) -> bool:
        return bool(self.entry.options.get(CONF_EVENT_ARCHIVE, False))

    def start(self) -> None:
        """Follow live alarms, backfill once and prune daily; options are read live."""
        from homeassistant.helpers.event import async_track_time_interval

        signal = ezviz_alarm_signal(self.entry.entry_id)
        self.entry.async_on_unload(async_dispatcher_connect(self.hass, signal, self._on_alarm))
        self.entry.async_on_unload(async_track_time_interval(self.hass, self.prune, DAY))
        self.entry.async_create_background_task(
            self.hass, self.backfill(), f"Vistoda EZVIZ event backfill {self.entry.entry_id}"
        )

    def _on_alarm(self, data: dict[str, Any] | None) -> None:
        # The listener also signals state changes with None.
        if data is not None and self.enabled:
            self.entry.async_create_background_task(
                self.hass, self.archive(data), f"Vistoda EZVIZ event archive {data['alarm_id']}"
            )

    async def archive(self, data: dict[str, Any]) -> None:
        """Archive one published alarm with its picture when it has one."""
        if self.enabled:
            jpeg = await self._picture(data["alarm_id"]) if data.get("picture") else None
            await self._write(data, jpeg)

    async def backfill(self) -> None:
        """Archive the app history until an alarm is already archived."""
        if not self.enabled:
            return
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
                jpeg = await self._picture(alarm.alarm_id) if alarm.picture_available else None
                written = await self._write(_record(alarm), jpeg)
                if not written:  # already archived (False) or mount unavailable (None)
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

    async def _write(self, alarm: dict[str, Any], jpeg: bytes | None) -> bool | None:
        try:
            written = await self.hass.async_add_executor_job(
                write_event, configured_mount(self.entry), PROVIDER, self.alias, alarm, jpeg
            )
        except (OSError, ValueError):
            self._report_unavailable()
            return None
        if self.unavailable:
            _LOGGER.info("EZVIZ event archive is available again")
            self.unavailable = False
        return written

    def _report_unavailable(self) -> None:
        if not self.unavailable:
            _LOGGER.warning("EZVIZ event archive is unavailable; check the network storage")
            self.unavailable = True


def _record(alarm) -> dict[str, Any]:
    return {
        "alarm_id": alarm.alarm_id,
        "occurred_at": alarm.occurred_at,
        "category": alarm.category,
        "alarm_type": alarm.alarm_type,
        "title": alarm.title,
    }
