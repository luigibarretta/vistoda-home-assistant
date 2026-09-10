"""Bounded client contract for persisted Ring cloud history."""

from dataclasses import dataclass
from urllib.parse import quote

from .errors import CannotConnectError

EVENT_TYPES = {"unlock", "live_view", "ding", "motion", "activity"}


@dataclass(frozen=True, slots=True)
class RingHistoryIdentity:
    device_name: str
    location_name: str
    city: str | None


@dataclass(frozen=True, slots=True)
class RingHistoryEvent:
    event_id: str
    event_type: str
    occurred_at: int


@dataclass(frozen=True, slots=True)
class RingHistoryPage:
    identity: RingHistoryIdentity
    events: tuple[RingHistoryEvent, ...]
    next_cursor: str | None


class RingHistoryClientMixin:
    """Consume one authenticated, server-paginated history page."""

    async def ring_history(
        self, alias: str, limit: int = 20, cursor: str | None = None
    ) -> RingHistoryPage:
        params = {"limit": limit}
        if cursor is not None:
            params["cursor"] = cursor
        payload = await self._json(
            "GET", f"/v1/devices/{quote(alias, safe='')}/history", params=params
        )
        try:
            raw_identity = payload["identity"]
            identity = RingHistoryIdentity(
                str(raw_identity["device_name"]),
                str(raw_identity["location_name"]),
                None if raw_identity["city"] is None else str(raw_identity["city"]),
            )
            events = tuple(
                RingHistoryEvent(
                    str(item["event_id"]), str(item["event_type"]), int(item["occurred_at"])
                )
                for item in payload["events"]
            )
            next_cursor = payload["next_cursor"]
        except (KeyError, TypeError, ValueError) as error:
            raise CannotConnectError from error
        if not _valid_text(identity.device_name) or not _valid_text(identity.location_name):
            raise CannotConnectError
        if identity.city is not None and not _valid_text(identity.city):
            raise CannotConnectError
        if not isinstance(next_cursor, (str, type(None))) or (
            next_cursor is not None and not _valid_cursor(next_cursor)
        ):
            raise CannotConnectError
        if len(events) > limit or any(not _valid_event(item) for item in events):
            raise CannotConnectError
        return RingHistoryPage(identity, events, next_cursor)


def _valid_event(event: RingHistoryEvent) -> bool:
    return (
        _valid_text(event.event_id) and event.event_type in EVENT_TYPES and event.occurred_at >= 0
    )


def _valid_text(value: str) -> bool:
    return bool(value) and len(value) <= 128 and value.isprintable()


def _valid_cursor(value: str) -> bool:
    return bool(value) and len(value) <= 32 and value.isascii() and value.isdecimal()
