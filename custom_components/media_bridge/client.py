"""Bounded async client for provider-specific Rust bridges."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

from aiohttp import ClientError, ClientSession, ClientTimeout

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
from .models import AudioSession, BridgeHealth, Enrollment, IceCandidate

JSON_LIMIT = 64 * 1024
IMAGE_LIMIT = 12 * 1024 * 1024
TIMEOUT = ClientTimeout(total=20, connect=5)
SESSION_TIMEOUT = ClientTimeout(total=30, connect=5)


class BridgeClient:
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

    async def start_ring_enrollment(self, email: str, password: str) -> Enrollment:
        payload = await self._json(
            "POST", "/v1/enrollments", json={"email": email, "password": password}
        )
        return parse_enrollment(payload)

    async def verify_ring_enrollment(self, enrollment_id: str, code: str) -> None:
        payload = await self._json(
            "POST", f"/v1/enrollments/{quote(enrollment_id, safe='')}", json={"code": code}
        )
        if payload.get("status") != "complete":
            raise CannotConnectError

    async def cancel_ring_enrollment(self, enrollment_id: str) -> None:
        response = await self._request("DELETE", f"/v1/enrollments/{quote(enrollment_id, safe='')}")
        async with response:
            await self._bounded(response, JSON_LIMIT)
            if response.status not in (204, 404):
                self._raise_status(response.status)

    async def start_ring_audio(self, alias: str, offer_sdp: str, mode: str) -> AudioSession:
        payload = await self._json(
            "POST",
            f"/v1/devices/{quote(alias, safe='')}/audio/sessions",
            json={"offer_sdp": offer_sdp, "mode": mode},
            timeout=SESSION_TIMEOUT,
        )
        return parse_audio_session(payload)

    async def stop_ring_audio(self, alias: str, session_id: str) -> None:
        path = f"/v1/devices/{quote(alias, safe='')}/audio/sessions/{quote(session_id, safe='')}"
        response = await self._request("DELETE", path)
        async with response:
            await self._bounded(response, JSON_LIMIT)
            if response.status != 204:
                self._raise_status(response.status)

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
        response = await self._request(method, path, authenticated=authenticated, **kwargs)
        async with response:
            body = await self._bounded(response, JSON_LIMIT)
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


def normalize_url(value: str) -> str:
    parts = urlsplit(value.strip())
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise ValueError("bridge URL must be HTTP(S)")
    if (
        parts.username
        or parts.password
        or parts.query
        or parts.fragment
        or parts.path not in ("", "/")
    ):
        raise ValueError("bridge URL cannot contain credentials, path, query or fragment")
    return urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip("/"), "", ""))


def parse_enrollment(payload: dict[str, Any]) -> Enrollment:
    try:
        result = Enrollment(
            enrollment_id=str(payload["enrollment_id"]),
            next_step=str(payload["next_step"]),
            expires_in=int(payload["expires_in"]),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise CannotConnectError from error
    if result.next_step not in ("otp", "complete") or not 0 <= result.expires_in <= 120:
        raise CannotConnectError
    return result


def error_code(body: bytes) -> str:
    try:
        payload = json.loads(body)
    except (ValueError, TypeError):
        return ""
    return payload.get("error", "") if isinstance(payload, dict) else ""


def parse_audio_session(payload: dict[str, Any]) -> AudioSession:
    try:
        raw_candidates = payload["ice_candidates"]
        candidates = tuple(
            IceCandidate(
                candidate=str(item["candidate"]),
                sdp_mline_index=int(item["sdp_mline_index"]),
            )
            for item in raw_candidates
        )
        result = AudioSession(
            session_id=str(payload["session_id"]),
            answer_sdp=str(payload["answer_sdp"]),
            ice_candidates=candidates,
            expires_in=int(payload["expires_in"]),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise CannotConnectError from error
    if (
        not result.session_id
        or not result.answer_sdp.startswith("v=0")
        or len(result.answer_sdp) > JSON_LIMIT
        or len(result.ice_candidates) > 64
        or not 1 <= result.expires_in <= 120
        or any(
            not candidate.candidate
            or len(candidate.candidate) > 4096
            or not 0 <= candidate.sdp_mline_index <= 16
            for candidate in result.ice_candidates
        )
    ):
        raise CannotConnectError
    return result
