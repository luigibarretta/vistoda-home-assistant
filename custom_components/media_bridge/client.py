"""Bounded async client for provider-specific Rust bridges."""

import json
import re
from typing import Any
from urllib.parse import quote, urlencode, urlsplit, urlunsplit

from aiohttp import ClientError, ClientSession, ClientTimeout

from .client_enrollment import EnrollmentClientMixin
from .client_helpers import error_code, normalize_url
from .client_provider_recordings import ProviderRecordingClientMixin
from .client_ring_audio import RingAudioClientMixin
from .client_ring_control import RingControlClientMixin
from .client_ring_events import RingEventClientMixin
from .client_ring_history import RingHistoryClientMixin
from .const import PROVIDER_RING
from .errors import (
    CannotConnectError,
    EnrollmentBusyError,
    EnrollmentExpiredError,
    InvalidBridgeAuthError,
    InvalidOtpError,
    InvalidVendorAuthError,
    RateLimitedError,
)
from .models import (
    BridgeHealth,
    Recording,
    parse_recording,
    parse_recording_archive,
)

JSON_LIMIT = 64 * 1024
IMAGE_LIMIT = 12 * 1024 * 1024
TIMEOUT = ClientTimeout(total=20, connect=5)
SESSION_TIMEOUT = ClientTimeout(total=30, connect=5)
RECORDING_LIST_LIMIT, RECORDING_UPLOAD_LIMIT = 512 * 1024, 8 * 1024 * 1024


class BridgeClient(
    ProviderRecordingClientMixin,
    RingAudioClientMixin,
    RingControlClientMixin,
    RingEventClientMixin,
    RingHistoryClientMixin,
    EnrollmentClientMixin,
):
    """Authenticate and consume one private bridge."""

    def __init__(self, session: ClientSession, base_url: str, token: str) -> None:
        self._session = session
        self.base_url = normalize_url(base_url)
        self._token = token

    async def health(self) -> BridgeHealth:
        payload = await self._json("GET", "/healthz", authenticated=False)
        if payload.get("status") != "ok" or not isinstance(payload.get("version"), str):
            raise CannotConnectError
        return BridgeHealth(version=payload["version"])

    async def validate(self, provider: str) -> None:
        await self.health()
        path = "/v1/devices" if provider == PROVIDER_RING else "/metrics"
        response = await self._request("GET", path)
        async with response:
            await self._bounded(response, JSON_LIMIT)
            if response.status == 401:
                raise InvalidBridgeAuthError
            if response.status != 200:
                raise CannotConnectError

    async def _empty(self, method: str, path: str, **kwargs: Any) -> None:
        response = await self._request(method, path, **kwargs)
        async with response:
            await self._bounded(response, JSON_LIMIT)
            if response.status != 204:
                self._raise_status(response.status)

    async def upload_ring_recording(
        self, alias: str, started_at: int, ended_at: int, media_type: str, media: bytes
    ) -> Recording:
        """Commit one bounded browser recording to the private archive."""
        if len(media) > RECORDING_UPLOAD_LIMIT:
            raise CannotConnectError
        response = await self._request(
            "POST",
            f"/v1/devices/{quote(alias, safe='')}/recordings",
            params={"started_at": started_at, "ended_at": ended_at},
            data=media,
            headers={"Content-Type": media_type},
            timeout=SESSION_TIMEOUT,
        )
        async with response:
            body = await self._bounded(response, JSON_LIMIT)
            if response.status != 201:
                self._raise_status(response.status, body)
            try:
                return parse_recording(json.loads(body))
            except (json.JSONDecodeError, UnicodeDecodeError) as error:
                raise CannotConnectError from error

    async def ring_recordings(self, alias: str) -> tuple[Recording, ...]:
        return (await self.ring_recording_archive(alias)).recordings

    async def ring_recording_archive(self, alias: str):
        """Return bounded records plus their effective display storage."""
        payload = await self._json(
            "GET",
            f"/v1/devices/{quote(alias, safe='')}/recordings",
            limit=RECORDING_LIST_LIMIT,
        )
        return parse_recording_archive(payload)

    async def read_ring_recording(self, alias: str, recording_id: str) -> tuple[str, bytes]:
        """Read one bounded private recording for an authenticated HA user."""
        path = f"/v1/devices/{quote(alias, safe='')}/recordings/{quote(recording_id, safe='')}"
        response = await self._request("GET", path, timeout=SESSION_TIMEOUT)
        async with response:
            body = await self._bounded(response, RECORDING_UPLOAD_LIMIT)
            if response.status != 200:
                self._raise_status(response.status, body)
            if response.content_type not in {"audio/mp4", "audio/webm"} or len(body) < 128:
                raise CannotConnectError
            return response.content_type, body

    async def delete_ring_recording(self, alias: str, recording_id: str) -> None:
        """Idempotently acknowledge and remove one private recording."""
        path = f"/v1/devices/{quote(alias, safe='')}/recordings/{quote(recording_id, safe='')}"
        await self._empty("DELETE", path)

    async def snapshot(self, alias: str) -> bytes:
        response = await self._request("GET", f"/v1/cameras/{quote(alias, safe='')}/snapshot.jpg")
        async with response:
            body = await self._bounded(response, IMAGE_LIMIT)
            if response.status == 401:
                raise InvalidBridgeAuthError
            if response.status != 200 or response.content_type != "image/jpeg":
                raise CannotConnectError
            return body

    async def ezviz_camera_identity(self, alias: str) -> str:
        """Read the authenticated immutable serial/channel binding for an alias."""
        payload = await self._json("GET", f"/v1/cameras/{quote(alias, safe='')}/identity")
        source_id = payload.get("source_id")
        if (
            payload.get("camera") != alias
            or not isinstance(source_id, str)
            or not re.fullmatch(
                r"[A-Za-z0-9_-]{1,64}:(?:[1-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-6])",
                source_id,
            )
        ):
            raise CannotConnectError
        return source_id

    def stream_url(self, alias: str, expected_binding: str) -> str:
        parts = urlsplit(self.base_url)
        auth = f"homeassistant:{quote(self._token, safe='')}@{parts.netloc}"
        path = f"/v1/cameras/{quote(alias, safe='')}/live.ts"
        query = urlencode({"expected_binding": expected_binding})
        return urlunsplit((parts.scheme, auth, path, query, ""))

    async def _json(
        self, method: str, path: str, *, authenticated: bool = True, **kwargs: Any
    ) -> dict[str, Any]:
        limit = kwargs.pop("limit", JSON_LIMIT)
        response = await self._request(method, path, authenticated=authenticated, **kwargs)
        async with response:
            body = await self._bounded(response, limit)
            if response.status < 200 or response.status >= 300:
                self._raise_status(response.status, body)
            try:
                payload = json.loads(body)
            except (ValueError, TypeError) as error:
                raise CannotConnectError from error
            if not isinstance(payload, dict):
                raise CannotConnectError
            return payload

    async def _request(self, method: str, path: str, *, authenticated: bool = True, **kwargs: Any):
        headers = {"Authorization": f"Bearer {self._token}"} if authenticated else {}
        headers.update(kwargs.pop("headers", {}))
        timeout = kwargs.pop("timeout", TIMEOUT)
        try:
            return await self._session.request(
                method, f"{self.base_url}{path}", headers=headers, timeout=timeout, **kwargs
            )
        except (ClientError, TimeoutError) as error:
            raise CannotConnectError from error

    @staticmethod
    async def _bounded(response: Any, limit: int) -> bytes:
        if response.content_length is not None and response.content_length > limit:
            raise CannotConnectError
        body = bytearray()
        async for chunk in response.content.iter_chunked(16 * 1024):
            if len(body) + len(chunk) > limit:
                raise CannotConnectError
            body.extend(chunk)
        return bytes(body)

    @staticmethod
    def _raise_status(status: int, body: bytes = b"") -> None:
        if status == 401:
            raise InvalidBridgeAuthError
        code = error_code(body)
        if status == 422 and code == "invalid_otp":
            raise InvalidOtpError
        if status == 422:
            raise InvalidVendorAuthError
        if status == 409:
            raise EnrollmentBusyError
        if status == 410:
            raise EnrollmentExpiredError
        if status == 429:
            raise RateLimitedError
        raise CannotConnectError
