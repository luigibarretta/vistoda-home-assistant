"""Lifecycle for the EZVIZ alarm long-poll consumer."""

import asyncio
import logging
import time
from contextlib import suppress

from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .client_ezviz_alarms import AlarmsUnsupportedError, EzvizAlarmCursor, alarm_picture_path
from .const import CONF_ALIAS, EVENT_EZVIZ_ALARM, ezviz_alarm_signal
from .errors import BridgeError
from .ezviz_binding import async_verify_native

_LOGGER = logging.getLogger(__name__)
# Older apps answer 404: check again rarely so an app update enables alarms.
UNSUPPORTED_RETRY_SECONDS = 3600
# A long poll that returns at once without news must not become a busy loop.
FAST_RESPONSE_SECONDS = 1.0
FAST_RESPONSE_PAUSE = 2


def camera_name(hass, entry) -> str:
    """Prefer the native EZVIZ camera name, then the configured alias."""
    from .ezviz_panel_metadata import panel_metadata

    return panel_metadata(hass, entry).get("device_name") or entry.data[CONF_ALIAS]


class EzvizAlarmListener:
    """Own one cancel-safe alarm cursor per EZVIZ camera entry."""

    def __init__(self, hass, entry, client, alias: str, *, verified: bool = False) -> None:
        self.hass = hass
        self.entry = entry
        self.client = client
        self.alias = alias
        self.cursor = EzvizAlarmCursor()
        self.task = None
        self._remove_stop_listener = None
        # Setup has just verified the binding; failures and app restarts re-verify.
        self._verified = verified
        self.supported: bool | None = None
        self.connected = False

    def start(self) -> None:
        if self.task is None:
            self._remove_stop_listener = self.hass.bus.async_listen_once(
                EVENT_HOMEASSISTANT_STOP, self._handle_home_assistant_stop
            )
            self.task = self.entry.async_create_background_task(
                self.hass,
                self._run(),
                f"Vistoda EZVIZ alarms {self.entry.entry_id}",
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
            tailing = self.cursor.after is not None
            started = time.monotonic()
            try:
                if not self._verified:
                    # Fail closed if the alias was retargeted to another camera.
                    await async_verify_native(self.entry, self.client)
                    self._verified = True
                batch = await self.client.ezviz_alarms(self.alias, self.cursor.after)
            except AlarmsUnsupportedError:
                failures = 0
                if self.supported is not False:
                    _LOGGER.info("Vistoda EZVIZ app has no alarm feed; update it to enable alarms")
                self._set_state(supported=False, connected=False)
                self.cursor = EzvizAlarmCursor()
                await asyncio.sleep(UNSUPPORTED_RETRY_SECONDS)
                continue
            except BridgeError:
                failures += 1
                self._verified = False
                self._set_state(supported=self.supported, connected=False)
                if failures == 6:
                    _LOGGER.warning("EZVIZ alarm listener is unavailable")
                await asyncio.sleep(min(60, 2 ** min(failures, 6)))
                continue
            failures = 0
            self._set_state(supported=True, connected=True)
            if self.cursor.generation not in (None, batch.generation):
                # The app restarted: verify the binding again before tailing.
                self._verified = False
            try:
                alarms = self.cursor.consume(batch)
                for alarm in alarms:
                    self._publish(alarm)
            except Exception:
                # One malformed alarm must not end the listener task.
                _LOGGER.exception("Could not publish an EZVIZ alarm")
                alarms = []
            if tailing and not alarms and time.monotonic() - started < FAST_RESPONSE_SECONDS:
                await asyncio.sleep(FAST_RESPONSE_PAUSE)

    def _set_state(self, *, supported: bool | None, connected: bool) -> None:
        if (supported, connected) == (self.supported, self.connected):
            return
        self.supported = supported
        self.connected = connected
        async_dispatcher_send(self.hass, ezviz_alarm_signal(self.entry.entry_id), None)

    def _publish(self, alarm) -> None:
        """Fire one automation event and one entity update per new alarm."""
        data = {
            "entry_id": self.entry.entry_id,
            "alias": self.alias,
            "camera_name": camera_name(self.hass, self.entry),
            "category": alarm.category,
            "alarm_type": alarm.alarm_type,
            "title": alarm.title,
            "occurred_at": alarm.occurred_at,
            "alarm_id": alarm.alarm_id,
            "picture": alarm_picture_path(self.entry.entry_id, alarm),
        }
        self.hass.bus.async_fire(EVENT_EZVIZ_ALARM, data)
        async_dispatcher_send(self.hass, ezviz_alarm_signal(self.entry.entry_id), data)
