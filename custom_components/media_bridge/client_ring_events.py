"""Bounded native Ring push-event client contract."""

from dataclasses import dataclass
from urllib.parse import quote
from uuid import UUID

from aiohttp import ClientTimeout

from .errors import CannotConnectError

EVENT_TIMEOUT = ClientTimeout(total=35, connect=5)


@dataclass(frozen=True, slots=True)
class RingPushEvent:
    sequence: int
    event_type: str
    occurred_at: int


@dataclass(frozen=True, slots=True)
class RingPushBatch:
    events: tuple[RingPushEvent, ...]
    next_sequence: int
    generation: str
    connected: bool
    device_id: str = ""
    cursor_reset: bool = False


@dataclass(slots=True)
class RingEventCursor:
    """Track one bridge generation without replaying an old process queue."""

    after: int | None = None
    generation: str | None = None

    def consume(self, batch: RingPushBatch) -> tuple[RingPushEvent, ...]:
        if self.generation is None:
            self.generation = batch.generation
        elif self.generation != batch.generation:
            self.generation = batch.generation
            self.after = batch.next_sequence
            return batch.events if batch.cursor_reset else ()
        if batch.cursor_reset:
            self.after = batch.next_sequence
            return batch.events
        if self.after is None:
            self.after = batch.next_sequence
            return ()
        self.after = max(self.after, batch.next_sequence)
        return batch.events


class RingEventClientMixin:
    """Consume the authenticated cursor/long-poll endpoint."""

    async def ring_events(
        self,
        alias: str,
        after: int | None,
        wait: int = 25,
        *,
        expected_device_id: str,
        generation: str | None = None,
    ) -> RingPushBatch:
        params = {"wait": wait, "expected_device_id": expected_device_id}
        if after is not None:
            params["after"] = after
        if generation is not None:
            params["generation"] = generation
        payload = await self._json(
            "GET",
            f"/v1/devices/{quote(alias, safe='')}/events",
            params=params,
            timeout=EVENT_TIMEOUT,
        )
        try:
            events = tuple(
                RingPushEvent(
                    sequence=int(item["sequence"]),
                    event_type=str(item["event_type"]),
                    occurred_at=int(item["occurred_at"]),
                )
                for item in payload["events"]
            )
            result = RingPushBatch(
                events=events,
                next_sequence=int(payload["next_sequence"]),
                generation=str(payload["generation"]),
                connected=payload["connected"],
                device_id=payload["device_id"],
                cursor_reset=payload["cursor_reset"],
            )
        except (KeyError, TypeError, ValueError) as error:
            raise CannotConnectError from error
        if (
            not isinstance(result.connected, bool)
            or not isinstance(result.cursor_reset, bool)
            or result.device_id != expected_device_id
            or result.next_sequence < (0 if result.cursor_reset else (after or 0))
            or len(events) > 128
            or not _valid_generation(result.generation)
            or (
                generation is not None
                and result.generation != generation
                and not result.cursor_reset
            )
            or (after is None and events and not result.cursor_reset)
            or any(
                event.sequence <= (0 if result.cursor_reset else after)
                or event.sequence > result.next_sequence
                or event.event_type not in {"ding", "intercom_unlock"}
                or event.occurred_at < 0
                for event in events
                if after is not None or result.cursor_reset
            )
        ):
            raise CannotConnectError
        return result


def _valid_generation(value: str) -> bool:
    try:
        return str(UUID(value)) == value
    except ValueError:
        return False
