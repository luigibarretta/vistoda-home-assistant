"""Validated Ring recording storage boundary."""

import json

import pytest

from custom_components.media_bridge.client import BridgeClient
from custom_components.media_bridge.errors import CannotConnectError


class FakeContent:
    def __init__(self, body: bytes) -> None:
        self.body = body

    async def iter_chunked(self, _size: int):
        yield self.body


class FakeResponse:
    def __init__(self, body: bytes) -> None:
        self.status = 200
        self.content_length = len(body)
        self.content_type = "application/json"
        self.content = FakeContent(body)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None


class FakeSession:
    def __init__(self, body: bytes) -> None:
        self.response = FakeResponse(body)

    async def request(self, _method, _url, **_kwargs):
        return self.response


def archive_payload(path: str) -> bytes:
    return json.dumps(
        {
            "storage": {
                "kind": "media",
                "directory": "/media/vistoda-ring",
                "user_visible": True,
            },
            "recordings": [
                {
                    "recording_id": "12345678-1234-1234-1234-123456789abc",
                    "started_at": 1786800000,
                    "ended_at": 1786800010,
                    "saved_at": 1786800011,
                    "bytes": 2048,
                    "media_type": "audio/webm",
                    "storage_path": path,
                }
            ],
        }
    ).encode()


async def test_archive_returns_exact_bounded_storage_paths() -> None:
    path = "/media/vistoda-ring/12345678-1234-1234-1234-123456789abc.webm"
    client = BridgeClient(
        FakeSession(archive_payload(path)),
        "http://bridge.local:8775",
        "x" * 32,
    )
    archive = await client.ring_recording_archive("entrance")
    assert archive.storage is not None
    assert archive.storage.directory == "/media/vistoda-ring"
    assert archive.recordings[0].storage_path == path


@pytest.mark.parametrize(
    "path",
    [
        "/share/outside.webm",
        "/media/vistoda-ring/../outside.webm",
        "relative.webm",
    ],
)
async def test_archive_rejects_paths_outside_the_declared_storage(path: str) -> None:
    client = BridgeClient(
        FakeSession(archive_payload(path)),
        "http://bridge.local:8775",
        "x" * 32,
    )
    with pytest.raises(CannotConnectError):
        await client.ring_recording_archive("entrance")
