"""Lifecycle for the native Ring push long-poll consumer."""

import asyncio
import logging
from contextlib import suppress

from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .client_ring_events import RingEventCursor
from .const import ring_event_signal
from .errors import BridgeError, CannotConnectError, ReauthRequiredError
from .outage import OUTAGE_GRACE_SECONDS, OutageClock
from .repairs import update_ring_push_issue, update_ring_push_silent_issue
from .ring_binding import CONF_RING_DEVICE_ID, valid_device_id
from .ring_missed_call import async_publish_missed_call

_LOGGER = logging.getLogger(__name__)
# A revoked Ring session is not a push outage; wait for the user to log in again.
REAUTH_RETRY_SECONDS = 300
# The engine rotates its push registration on its own; a rotation with a few
# rejected attempts takes minutes. Only a continuous outage this long needs a person.
PUSH_OUTAGE_GRACE_SECONDS = OUTAGE_GRACE_SECONDS


class RingEventListener:
    """Own one cancel-safe event cursor per config entry."""

    def __init__(self, hass, entry, client, alias: str, history) -> None:
        self.hass = hass
        self.entry = entry
        self.client = client
        self.alias = alias
        self.history = history
        self.cursor = RingEventCursor()
        self.task = None
        self._remove_stop_listener = None
        self.connected = False
        self.reauth_required = False
        self.push_outage = OutageClock(PUSH_OUTAGE_GRACE_SECONDS)

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
                expected_device_id = self.entry.data.get(CONF_RING_DEVICE_ID)
                if not valid_device_id(expected_device_id):
                    raise CannotConnectError
                batch = await self.client.ring_events(
                    self.alias,
                    self.cursor.after,
                    expected_device_id=expected_device_id,
                    generation=self.cursor.generation,
                )
            except ReauthRequiredError:
                self.connected = False
                if not self.reauth_required:
                    self.reauth_required = True
                    _LOGGER.warning("Ring session was revoked; a new login is required")
                    self.entry.async_start_reauth(self.hass)
                await asyncio.sleep(REAUTH_RETRY_SECONDS)
                continue
            except BridgeError:
                # The app itself is unreachable: bridge_unavailable owns that outage.
                # Whether Ring accepts the push registration is unknown, so the push
                # clock restarts from the app's next real answer.
                failures += 1
                self.connected = False
                self.push_outage.up()
                if failures in {1, 6}:
                    _LOGGER.warning("Native Ring event listener is unavailable")
                await asyncio.sleep(min(60, 2 ** min(failures, 6)))
                continue
            self.reauth_required = False
            self.connected = batch.connected
            await self._handle_push_health(batch)
            if batch.connected:
                failures = 0
                self.push_outage.up()
                update_ring_push_issue(self.hass, self.entry, available=True)
            else:
                failures += 1
                self._mark_push_down()
            for event in self.cursor.consume(batch):
                event_type = "unlock" if event.event_type == "intercom_unlock" else "ding"
                await self.history.async_record(
                    event_type,
                    event.occurred_at,
                    f"observed:native:{event.sequence}",
                    origin=event.origin,
                    actor=event.actor,
                )
                async_dispatcher_send(self.hass, ring_event_signal(self.entry.entry_id), event)

    def _mark_push_down(self) -> None:
        """Raise the repair only once the app kept reporting no push past the grace."""
        if self.push_outage.down():
            update_ring_push_issue(self.hass, self.entry, available=False)

    async def _handle_push_health(self, batch) -> None:
        """Apply optional engine hints; older engines omit them entirely."""
        if batch.push_degraded is not None:
            update_ring_push_silent_issue(self.hass, self.entry, batch.push_degraded)
        if batch.last_missed_ding_at is not None:
            await async_publish_missed_call(self.history, batch.last_missed_ding_at)
