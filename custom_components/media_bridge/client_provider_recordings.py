"""Bounded client operations for provider-local video recordings."""

from typing import Any
from urllib.parse import quote

from .errors import CannotConnectError

RECORDING_LIST_LIMIT = 512 * 1024
SESSION_TIMEOUT_SECONDS = 90
STATUSES = {"pending", "recording", "ready", "failed"}


class ProviderRecordingClientMixin:
    """Consume standalone recording contracts without exposing bridge tokens."""

    async def provider_recordings(self) -> list[dict[str, Any]]:
        payload = await self._json("GET", "/v1/recordings", limit=RECORDING_LIST_LIMIT)
        raw = payload.get("recordings")
        if not isinstance(raw, list) or len(raw) > 1_000:
            raise CannotConnectError
        return [self._recording(item) for item in raw]

    async def create_provider_recording(
        self,
        alias: str,
        duration_seconds: int,
        request_id: str,
    ) -> dict[str, Any]:
        return self._recording(
            await self._json(
                "POST",
                f"/v1/cameras/{quote(alias, safe='')}/recordings",
                json={"duration_seconds": duration_seconds},
                headers={"Idempotency-Key": request_id},
            )
        )

    async def delete_provider_recording(self, recording_id: str) -> None:
        await self._empty("DELETE", f"/v1/recordings/{quote(recording_id, safe='')}")

    async def open_provider_recording(self, recording_id: str):
        return await self._request(
            "GET",
            f"/v1/recordings/{quote(recording_id, safe='')}/media",
            timeout=None,
        )

    @staticmethod
    def _recording(value: object) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise CannotConnectError
        item = value
        required = {
            "recording_id": str,
            "camera": str,
            "status": str,
            "requested_at": str,
            "requested_duration_seconds": int,
            "media_type": str,
        }
        if any(not isinstance(item.get(key), expected) for key, expected in required.items()):
            raise CannotConnectError
        if item["status"] not in STATUSES or item["media_type"] != "video/mpeg":
            raise CannotConnectError
        optional = ("started_at", "completed_at", "actual_duration_seconds", "bytes", "sha256")
        return {**{key: item[key] for key in required}, **{key: item.get(key) for key in optional}}
