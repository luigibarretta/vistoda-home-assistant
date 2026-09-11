"""Physically pinned Ring audio client operations."""

from typing import Any
from urllib.parse import quote, urlencode, urlsplit, urlunsplit

from aiohttp import ClientTimeout, ClientWSTimeout

from .models import AudioSession, parse_audio_session

AUDIO_SESSION_TIMEOUT = ClientTimeout(total=30, connect=5)
RELAY_TIMEOUT = ClientWSTimeout(ws_receive=125, ws_close=5)


class RingAudioClientMixin:
    """Start, relay and stop one audio session for an exact Ring device."""

    _session: Any
    _token: str
    base_url: str

    async def start_ring_audio(
        self,
        alias: str,
        offer_sdp: str,
        mode: str,
        ice_gathering_ms: int,
        *,
        expected_device_id: str,
    ) -> AudioSession:
        payload = await self._json(
            "POST",
            f"/v1/devices/{quote(alias, safe='')}/audio/sessions",
            json={
                "offer_sdp": offer_sdp,
                "mode": mode,
                "ice_gathering_ms": ice_gathering_ms,
                "expected_device_id": expected_device_id,
            },
            timeout=AUDIO_SESSION_TIMEOUT,
        )
        return parse_audio_session(payload)

    async def stop_ring_audio(
        self,
        alias: str,
        session_id: str,
        reason: str,
        *,
        expected_device_id: str,
    ) -> None:
        path = f"/v1/devices/{quote(alias, safe='')}/audio/sessions/{quote(session_id, safe='')}"
        response = await self._request(
            "DELETE",
            path,
            params={"reason": reason, "expected_device_id": expected_device_id},
        )
        async with response:
            await self._bounded(response, 64 * 1024)
            if response.status != 204:
                self._raise_status(response.status)

    def ring_relay(self, alias: str, *, expected_device_id: str):
        parts = urlsplit(self.base_url)
        scheme = "wss" if parts.scheme == "https" else "ws"
        path = f"/v1/devices/{quote(alias, safe='')}/audio/relay"
        query = urlencode({"expected_device_id": expected_device_id})
        url = urlunsplit((scheme, parts.netloc, path, query, ""))
        return self._session.ws_connect(
            url,
            headers={"Authorization": f"Bearer {self._token}"},
            timeout=RELAY_TIMEOUT,
            heartbeat=15,
            max_msg_size=2 * 1024,
        )
