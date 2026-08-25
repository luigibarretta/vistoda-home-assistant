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
            return ()
        if self.after is None:
            self.after = batch.next_sequence
            return ()
        self.after = max(self.after, batch.next_sequence)
        return batch.events


class RingEventClientMixin:
    """Consume the authenticated cursor/long-poll endpoint."""

    async def ring_events(self, alias: str, after: int | None, wait: int = 25) -> RingPushBatch:
        params = {"wait": wait}
        if after is not None:
            params["after"] = after
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
            )
        except (KeyError, TypeError, ValueError) as error:
            raise CannotConnectError from error
        if (
            not isinstance(result.connected, bool)
            or result.next_sequence < (after or 0)
            or len(events) > 128
            or not _valid_generation(result.generation)
            or (after is None and events)
            or any(
                event.sequence <= after
                or event.sequence > result.next_sequence
                or event.event_type not in {"ding", "intercom_unlock"}
                or event.occurred_at < 0
                for event in events
            )
        ):
            raise CannotConnectError
        return result


def _valid_generation(value: str) -> bool:
    try:
        return str(UUID(value)) == value
    except ValueError:
        return False
