"""Bounded async client for provider-specific Rust bridges."""

import json
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

from aiohttp import ClientError, ClientSession, ClientTimeout, ClientWSTimeout

from .client_enrollment import EnrollmentClientMixin
from .client_helpers import error_code, normalize_url
from .client_ring_events import RingEventClientMixin
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
    AudioSession,
    BridgeHealth,
    Recording,
    parse_audio_session,
    parse_recording,
    parse_recording_archive,
    parse_ring_status,
)

JSON_LIMIT = 64 * 1024
IMAGE_LIMIT = 12 * 1024 * 1024
TIMEOUT = ClientTimeout(total=20, connect=5)
SESSION_TIMEOUT = ClientTimeout(total=30, connect=5)
RECORDING_LIST_LIMIT, RECORDING_UPLOAD_LIMIT = 512 * 1024, 8 * 1024 * 1024
RELAY_TIMEOUT = ClientWSTimeout(ws_receive=125, ws_close=5)


class BridgeClient(RingEventClientMixin, EnrollmentClientMixin):
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

    async def start_ring_audio(
        self, alias: str, offer_sdp: str, mode: str, ice_gathering_ms: int
    ) -> AudioSession:
        payload = await self._json(
            "POST",
            f"/v1/devices/{quote(alias, safe='')}/audio/sessions",
            json={
                "offer_sdp": offer_sdp,
                "mode": mode,
                "ice_gathering_ms": ice_gathering_ms,
            },
            timeout=SESSION_TIMEOUT,
        )
        return parse_audio_session(payload)

    async def stop_ring_audio(self, alias: str, session_id: str, reason: str) -> None:
        path = f"/v1/devices/{quote(alias, safe='')}/audio/sessions/{quote(session_id, safe='')}"
        response = await self._request("DELETE", path, params={"reason": reason})
        async with response:
            await self._bounded(response, JSON_LIMIT)
            if response.status != 204:
                self._raise_status(response.status)

    def ring_relay(self, alias: str):
        """Open one private PCMU relay without exposing bridge credentials."""
        parts = urlsplit(self.base_url)
        scheme = "wss" if parts.scheme == "https" else "ws"
        path = f"/v1/devices/{quote(alias, safe='')}/audio/relay"
        url = urlunsplit((scheme, parts.netloc, path, "", ""))
        return self._session.ws_connect(
            url,
            headers={"Authorization": f"Bearer {self._token}"},
            timeout=RELAY_TIMEOUT,
            heartbeat=15,
            max_msg_size=2 * 1024,
        )

    async def ring_status(self, alias: str):
        """Return native Ring Intercom battery, connectivity and levels."""
        payload = await self._json("GET", f"/v1/devices/{quote(alias, safe='')}/status")
        return parse_ring_status(payload)

    async def unlock_ring(self, alias: str) -> None:
        """Issue one native unlock request without retries in Home Assistant."""
        await self._empty("POST", f"/v1/devices/{quote(alias, safe='')}/unlock")

    async def set_ring_volume(self, alias: str, setting: str, value: int) -> None:
        """Set exactly one bounded native volume."""
        if setting not in {"doorbell_volume", "mic_volume", "voice_volume"}:
            raise ValueError("unknown Ring volume")
        await self._empty(
            "PATCH",
            f"/v1/devices/{quote(alias, safe='')}/settings",
            json={setting: value},
        )

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

    def stream_url(self, alias: str) -> str:
        parts = urlsplit(self.base_url)
        auth = f"homeassistant:{quote(self._token, safe='')}@{parts.netloc}"
        path = f"/v1/cameras/{quote(alias, safe='')}/live.ts"
        return urlunsplit((parts.scheme, auth, path, "", ""))

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
