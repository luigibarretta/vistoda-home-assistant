"""Bounded Vistoda EZVIZ 0.9 encryption, microSD and SD-record contracts."""

import json
from dataclasses import dataclass
from datetime import date
from urllib.parse import quote

from .errors import CannotConnectError

KEY_SOURCES = ("option", "cloud", "none")
STORAGE_STATUSES = ("ok", "no_card", "unformatted", "error", "unknown")
RECORD_TYPES = ("event", "continuous", "other")
MAX_RECORDS = 500
MEDIA_LIMIT = 16 * 1024
RECORDS_LIMIT = 256 * 1024
# Largest plausible microSD capacity (2 TB) in MB; anything above is bogus.
MAX_CAPACITY_MB = 2 * 1024 * 1024


class EzvizFeatureUnsupportedError(CannotConnectError):
    """The Vistoda EZVIZ app predates this route (HTTP 404)."""


@dataclass(frozen=True, slots=True)
class EzvizEncryption:
    video_encrypted: bool | None
    key_source: str | None


@dataclass(frozen=True, slots=True)
class EzvizStorage:
    status: str
    capacity_mb: int | None


@dataclass(frozen=True, slots=True)
class EzvizSdRecord:
    start: int
    end: int
    record_type: str


def _count(value, maximum: int) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= maximum:
        return None
    return value


def parse_encryption(payload: dict) -> EzvizEncryption:
    """Unknown values degrade to None instead of failing the whole document."""
    encrypted = payload.get("video_encrypted")
    source = payload.get("key_source")
    return EzvizEncryption(
        video_encrypted=encrypted if isinstance(encrypted, bool) else None,
        key_source=source if source in KEY_SOURCES else None,
    )


def parse_storage(payload: dict) -> EzvizStorage:
    status = payload.get("status")
    return EzvizStorage(
        status=status if status in STORAGE_STATUSES else "unknown",
        capacity_mb=_count(payload.get("capacity_mb"), MAX_CAPACITY_MB),
    )


def parse_sd_records(payload: dict) -> tuple[EzvizSdRecord, ...]:
    """Keep at most 500 well-formed ranges, sorted by start; skip malformed items."""
    raw = payload.get("records")
    if not isinstance(raw, list):
        raise CannotConnectError
    records = []
    for item in raw[:MAX_RECORDS]:
        if not isinstance(item, dict):
            continue
        start = _count(item.get("start"), 2**63 - 1)
        end = _count(item.get("end"), 2**63 - 1)
        if start is None or end is None or end < start:
            continue
        kind = item.get("type")
        records.append(EzvizSdRecord(start, end, kind if kind in RECORD_TYPES else "other"))
    return tuple(sorted(records, key=lambda record: (record.start, record.end)))


class EzvizMediaClientMixin:
    """Read-only EZVIZ app routes; a 404 means the app is older than 0.9."""

    async def _ezviz_feature(self, alias: str, feature: str, limit: int, **kwargs) -> dict:
        path = f"/v1/cameras/{quote(alias, safe='')}/{feature}"
        response = await self._request("GET", path, **kwargs)
        async with response:
            body = await self._bounded(response, limit)
            if response.status == 404:
                raise EzvizFeatureUnsupportedError
            if response.status != 200:
                self._raise_status(response.status, body)
        try:
            payload = json.loads(body)
        except (ValueError, TypeError) as error:
            raise CannotConnectError from error
        if not isinstance(payload, dict):
            raise CannotConnectError
        return payload

    async def ezviz_encryption(self, alias: str) -> EzvizEncryption:
        return parse_encryption(await self._ezviz_feature(alias, "encryption", MEDIA_LIMIT))

    async def ezviz_storage(self, alias: str) -> EzvizStorage:
        return parse_storage(await self._ezviz_feature(alias, "storage", MEDIA_LIMIT))

    async def ezviz_sd_records(self, alias: str, day: date) -> tuple[EzvizSdRecord, ...]:
        payload = await self._ezviz_feature(
            alias, "sd-records", RECORDS_LIMIT, params={"date": day.isoformat()}
        )
        return parse_sd_records(payload)
