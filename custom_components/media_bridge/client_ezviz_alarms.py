"""Bounded EZVIZ alarm cursor and picture client contract."""

import json
import re
from dataclasses import dataclass
from urllib.parse import quote

from aiohttp import ClientTimeout

from .errors import CannotConnectError

ALARM_TIMEOUT = ClientTimeout(total=35, connect=5)
PICTURE_TIMEOUT = ClientTimeout(total=20, connect=5)
ALARM_LIST_LIMIT = 256 * 1024
PICTURE_LIMIT = 8 * 1024 * 1024
MAX_WAIT = 25
MAX_EVENTS = 128
CATEGORIES = (
    "motion",
    "person",
    "vehicle",
    "doorbell",
    "sound",
    "pet",
    "offline",
    "tamper",
    "other",
)
# Only URL-safe identifiers become picture paths; anything else keeps no picture.
PICTURE_ID = re.compile(r"[A-Za-z0-9_-]{1,128}")


class AlarmsUnsupportedError(CannotConnectError):
    """The Vistoda EZVIZ app predates the alarm contract (HTTP 404)."""


@dataclass(frozen=True, slots=True)
class EzvizAlarm:
    sequence: int
    alarm_id: str
    occurred_at: int
    alarm_type: int
    category: str
    title: str
    has_picture: bool

    @property
    def picture_available(self) -> bool:
        return self.has_picture and valid_picture_id(self.alarm_id)


@dataclass(frozen=True, slots=True)
class EzvizAlarmBatch:
    events: tuple[EzvizAlarm, ...]
    next_sequence: int
    generation: str


@dataclass(slots=True)
class EzvizAlarmCursor:
    """Tail one app generation; the first batch and every restart only prime."""

    after: int | None = None
    generation: str | None = None

    def consume(self, batch: EzvizAlarmBatch) -> tuple[EzvizAlarm, ...]:
        previous = self.after
        if (
            previous is None
            or self.generation != batch.generation
            or batch.next_sequence < previous
        ):
            # Startup, app restart or a rewound queue: never replay history.
            self.generation = batch.generation
            self.after = batch.next_sequence
            return ()
        self.after = batch.next_sequence
        return tuple(event for event in batch.events if event.sequence > previous)


def valid_picture_id(value) -> bool:
    return isinstance(value, str) and PICTURE_ID.fullmatch(value) is not None


def alarm_picture_path(entry_id: str, alarm: EzvizAlarm) -> str | None:
    """Return the authenticated Home Assistant picture path, or None."""
    if not alarm.picture_available:
        return None
    return f"/api/media_bridge/ezviz/{entry_id}/alarms/{alarm.alarm_id}.jpg"


def _int(value, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError
    return value


def _generation(value) -> str:
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, str) and 0 < len(value) <= 64 and value.isprintable():
        return value
    raise ValueError


def _title(value) -> str:
    """Keep vendor text short and printable; markup is escaped by every consumer."""
    if not isinstance(value, str):
        return ""
    printable = "".join(c if c.isprintable() else " " for c in value)
    return " ".join(printable.split())[:160]


def parse_alarm(item) -> EzvizAlarm:
    alarm_id = item["id"]
    if not isinstance(alarm_id, str) or not 0 < len(alarm_id) <= 128 or "/" in alarm_id:
        raise ValueError
    category = item.get("category")
    has_picture = item.get("has_picture")
    return EzvizAlarm(
        sequence=_int(item["sequence"]),
        alarm_id=alarm_id,
        occurred_at=_int(item["occurred_at"]),
        alarm_type=_int(item["alarm_type"], minimum=-(2**31)),
        category=category if category in CATEGORIES else "other",
        title=_title(item.get("title")),
        has_picture=has_picture if isinstance(has_picture, bool) else False,
    )


def parse_alarm_batch(payload, camera: str) -> EzvizAlarmBatch:
    try:
        raw = payload["events"]
        if payload["camera"] != camera or not isinstance(raw, list) or len(raw) > MAX_EVENTS:
            raise ValueError
        batch = EzvizAlarmBatch(
            events=tuple(parse_alarm(item) for item in raw),
            next_sequence=_int(payload["next_sequence"]),
            generation=_generation(payload["generation"]),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise CannotConnectError from error
    if any(event.sequence > batch.next_sequence for event in batch.events):
        raise CannotConnectError
    return batch


class EzvizAlarmClientMixin:
    """Consume the authenticated alarm cursor without exposing the bridge token."""

    async def ezviz_alarms(
        self, alias: str, after: int | None = None, wait: int = MAX_WAIT
    ) -> EzvizAlarmBatch:
        """Long-poll new alarms; without a cursor return recent history at once."""
        params = {}
        if after is not None:
            params = {"after": after, "wait": max(0, min(wait, MAX_WAIT))}
        response = await self._request(
            "GET",
            f"/v1/cameras/{quote(alias, safe='')}/alarms",
            params=params,
            timeout=ALARM_TIMEOUT,
        )
        async with response:
            body = await self._bounded(response, ALARM_LIST_LIMIT)
            if response.status == 404:
                raise AlarmsUnsupportedError
            if response.status != 200:
                self._raise_status(response.status, body)
            try:
                payload = json.loads(body)
            except (ValueError, TypeError) as error:
                raise CannotConnectError from error
        if not isinstance(payload, dict):
            raise CannotConnectError
        return parse_alarm_batch(payload, alias)

    async def ezviz_alarm_picture(self, alias: str, alarm_id: str) -> bytes | None:
        """Read one bounded JPEG; None means the app has no picture for it."""
        if not valid_picture_id(alarm_id):
            return None
        path = f"/v1/cameras/{quote(alias, safe='')}/alarms/{alarm_id}/picture.jpg"
        response = await self._request("GET", path, timeout=PICTURE_TIMEOUT)
        async with response:
            body = await self._bounded(response, PICTURE_LIMIT)
            if response.status == 404:
                return None
            if response.status != 200:
                self._raise_status(response.status, body)
            if response.content_type != "image/jpeg" or not body.startswith(b"\xff\xd8"):
                raise CannotConnectError
            return body
