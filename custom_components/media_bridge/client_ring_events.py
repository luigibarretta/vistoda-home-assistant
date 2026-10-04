"""Bounded native Ring push-event client contract."""

from dataclasses import dataclass
from urllib.parse import quote
from uuid import UUID

from aiohttp import ClientTimeout

from .errors import CannotConnectError

EVENT_TIMEOUT = ClientTimeout(total=35, connect=5)
UNLOCK_ORIGINS = frozenset({"user", "device", "code", "delivery"})


@dataclass(frozen=True, slots=True)
class RingPushEvent:
    sequence: int
    event_type: str
    occurred_at: int
    origin: str = ""
    actor: str = ""


def _origin(value) -> str:
    """Accept only Ring's unlock origins; anything else is unknown."""
    return value if value in UNLOCK_ORIGINS else ""


def _actor(value) -> str:
    """Accept a short printable display name; anything else is unknown."""
    if not isinstance(value, str) or not 0 < len(value) <= 64 or not value.isprintable():
        return ""
    return value


@dataclass(frozen=True, slots=True)
class RingPushBatch:
    events: tuple[RingPushEvent, ...]
    next_sequence: int
    generation: str
    connected: bool
    device_id: str = ""
    cursor_reset: bool = False
    # Optional engine hints; None means an older engine that omits them.
    push_degraded: bool | None = None
    last_missed_ding_at: int | None = None


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
                    origin=_origin(item.get("origin")),
                    actor=_actor(item.get("actor")),
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
                push_degraded=_optional_bool(payload.get("push_degraded")),
                last_missed_ding_at=_optional_timestamp(payload.get("last_missed_ding_at")),
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


def _optional_bool(value) -> bool | None:
    """Ignore malformed optional hints instead of failing the whole batch."""
    return value if isinstance(value, bool) else None


def _optional_timestamp(value) -> int | None:
    """Accept a non-negative epoch-second timestamp; anything else is unknown."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _valid_generation(value: str) -> bool:
    try:
        return str(UUID(value)) == value
    except ValueError:
        return False
