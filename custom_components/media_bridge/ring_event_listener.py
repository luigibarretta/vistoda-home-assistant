"""Lifecycle for the native Ring push long-poll consumer."""

import asyncio
import logging
from contextlib import suppress

from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .client_ring_events import RingEventCursor
from .const import ring_event_signal
from .errors import BridgeError
from .repairs import update_ring_push_issue

_LOGGER = logging.getLogger(__name__)


class RingEventListener:
    """Own one cancel-safe event cursor per config entry."""

    def __init__(self, hass, entry, client, alias: str) -> None:
        self.hass = hass
        self.entry = entry
        self.client = client
        self.alias = alias
        self.cursor = RingEventCursor()
        self.task = None
        self._remove_stop_listener = None
        self.connected = False

    def start(self) -> None:
        if self.task is None:
            self._remove_stop_listener = self.hass.bus.async_listen_once(
                EVENT_HOMEASSISTANT_STOP, self._handle_home_assistant_stop
            )
            self.task = self.entry.async_create_background_task(
                self.hass,
                self._run(),
                f"Vistoda Ring events {self.entry.entry_id}",
            )

    async def stop(self) -> None:
        if self._remove_stop_listener is not None:
            self._remove_stop_listener()
            self._remove_stop_listener = None
        if self.task is None:
            return
        self.task.cancel()
        with suppress(asyncio.CancelledError):
            await self.task
        self.task = None
        self.connected = False

    async def _handle_home_assistant_stop(self, _event) -> None:
        self._remove_stop_listener = None
        await self.stop()

    async def _run(self) -> None:
        failures = 0
        while True:
            try:
                batch = await self.client.ring_events(self.alias, self.cursor.after)
            except BridgeError:
                failures += 1
                self.connected = False
                if failures >= 6:
                    update_ring_push_issue(self.hass, self.entry, available=False)
                if failures in {1, 6}:
                    _LOGGER.warning("Native Ring event listener is unavailable")
                await asyncio.sleep(min(60, 2 ** min(failures, 6)))
                continue
            self.connected = batch.connected
            if batch.connected:
                failures = 0
                update_ring_push_issue(self.hass, self.entry, available=True)
            else:
                failures += 1
                if failures >= 6:
                    update_ring_push_issue(self.hass, self.entry, available=False)
            for event in self.cursor.consume(batch):
                async_dispatcher_send(self.hass, ring_event_signal(self.entry.entry_id), event)
