"""Provider-local archive client contracts."""

import json

import pytest

from custom_components.media_bridge.client import BridgeClient


class FakeContent:
    def __init__(self, body: bytes) -> None:
        self.body = body

    async def iter_chunked(self, _size: int):
        yield self.body


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.body = json.dumps(payload).encode()
        self.status = 200
        self.content = FakeContent(self.body)
        self.content_length = len(self.body)
        self.content_type = "application/json"

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None


class FakeSession:
    def __init__(self, payload: dict) -> None:
        self.response = FakeResponse(payload)
        self.last_request = None

    async def request(self, method, url, **kwargs):
        self.last_request = (method, url, kwargs)
        return self.response


async def test_ezviz_recording_inventory_is_server_paginated() -> None:
    manifest = {
        "recording_id": "00000000-0000-4000-8000-000000000001",
        "camera": "front",
        "status": "ready",
        "requested_at": "2026-09-09T20:00:00Z",
        "requested_duration_seconds": 30,
        "media_type": "video/mpeg",
    }
    pagination = {
        "page": 2,
        "page_size": 10,
        "total_items": 12,
        "total_pages": 2,
        "has_previous": True,
        "has_next": False,
    }
    storage = {
        "directory": "/data/recordings",
        "scope": "addon_private",
        "used_bytes": 4096,
        "quota_bytes": 1024 * 1024,
        "available_bytes": 1024 * 1024 - 4096,
    }
    session = FakeSession({"recordings": [manifest], "pagination": pagination, "storage": storage})
    client = BridgeClient(session, "http://bridge.local:8765", "x" * 32)
    result = await client.provider_recordings(2, 10, "front")
    assert result["recordings"][0]["recording_id"] == manifest["recording_id"]
    assert result["pagination"] == pagination
    assert result["storage"] == storage
    assert session.last_request[2]["params"] == {"page": 2, "page_size": 10, "camera": "front"}


@pytest.mark.parametrize("media_type", ["video/mpeg", "video/mp2t"])
def test_ezviz_client_preserves_the_recording_container_type(media_type):
    manifest = {
        "recording_id": "00000000-0000-4000-8000-000000000001",
        "camera": "front",
        "status": "ready",
        "requested_at": "2026-09-11T20:00:00Z",
        "requested_duration_seconds": 30,
        "media_type": media_type,
    }
    assert BridgeClient._recording(manifest)["media_type"] == media_type
