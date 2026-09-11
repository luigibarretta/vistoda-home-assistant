"""Bounded client operations for provider-local video recordings."""

from typing import Any
from urllib.parse import quote

from .errors import CannotConnectError

RECORDING_LIST_LIMIT = 512 * 1024
SESSION_TIMEOUT_SECONDS = 90
STATUSES = {"pending", "recording", "ready", "failed"}


class ProviderRecordingClientMixin:
    """Consume standalone recording contracts without exposing bridge tokens."""

    async def provider_recordings(
        self,
        page: int = 1,
        page_size: int = 20,
        camera: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, str | int] = {"page": page, "page_size": page_size}
        if camera:
            params["camera"] = camera
        payload = await self._json(
            "GET", "/v1/recordings", params=params, limit=RECORDING_LIST_LIMIT
        )
        raw = payload.get("recordings")
        pagination = payload.get("pagination")
        storage = payload.get("storage")
        if (
            not isinstance(raw, list)
            or len(raw) > 50
            or not self._pagination(pagination)
            or not self._storage(storage)
        ):
            raise CannotConnectError
        return {
            "recordings": [self._recording(item) for item in raw],
            "pagination": pagination,
            "storage": storage,
        }

    async def provider_recording(self, recording_id: str) -> dict[str, Any]:
        return self._recording(
            await self._json(
                "GET",
                f"/v1/recordings/{quote(recording_id, safe='')}",
                limit=RECORDING_LIST_LIMIT,
            )
        )

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

    async def open_provider_playback(self, recording_id: str):
        return await self._request(
            "GET",
            f"/v1/recordings/{quote(recording_id, safe='')}/playback.mp4",
            timeout=None,
        )

    @staticmethod
    def _pagination(value: object) -> bool:
        if not isinstance(value, dict):
            return False
        integers = ("page", "page_size", "total_items", "total_pages")
        return (
            all(isinstance(value.get(key), int) for key in integers)
            and 1 <= value["page_size"] <= 50
            and value["page"] >= 1
            and value["total_items"] >= 0
            and value["total_pages"] >= 1
            and isinstance(value.get("has_previous"), bool)
            and isinstance(value.get("has_next"), bool)
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
        if item["status"] not in STATUSES or item["media_type"] not in {"video/mpeg", "video/mp2t"}:
            raise CannotConnectError
        optional = ("started_at", "completed_at", "actual_duration_seconds", "bytes", "sha256")
        return {**{key: item[key] for key in required}, **{key: item.get(key) for key in optional}}

    @staticmethod
    def _storage(value: object) -> bool:
        if not isinstance(value, dict):
            return False
        directory = value.get("directory")
        integers = ("used_bytes", "quota_bytes", "available_bytes")
        return (
            isinstance(directory, str)
            and directory.startswith("/")
            and len(directory) <= 1024
            and ".." not in directory.split("/")
            and value.get("scope") == "addon_private"
            and all(isinstance(value.get(key), int) and value[key] >= 0 for key in integers)
            and value["used_bytes"] <= value["quota_bytes"]
            and value["available_bytes"] <= value["quota_bytes"]
        )
