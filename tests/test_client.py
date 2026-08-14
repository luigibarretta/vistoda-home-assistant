"""Contract tests for the bounded provider-neutral client."""

import json

import pytest

from custom_components.media_bridge.client import BridgeClient, normalize_url
from custom_components.media_bridge.errors import InvalidOtpError


class FakeContent:
    def __init__(self, body: bytes) -> None:
        self._body = body

    async def iter_chunked(self, _size: int):
        yield self._body


class FakeResponse:
    def __init__(self, status: int, body: bytes, content_type: str = "application/json") -> None:
        self.status = status
        self.content = FakeContent(body)
        self.content_length = len(body)
        self.content_type = content_type

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None


class FakeSession:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses
        self.requests = []

    async def request(self, method, url, **kwargs):
        self.requests.append((method, url, kwargs))
        return self.responses.pop(0)


def response(status: int, payload: dict) -> FakeResponse:
    return FakeResponse(status, json.dumps(payload).encode())


@pytest.mark.asyncio
async def test_ring_enrollment_is_two_step_and_token_is_a_header() -> None:
    session = FakeSession(
        [response(200, {"enrollment_id": "synthetic", "next_step": "otp", "expires_in": 120})]
    )
    client = BridgeClient(session, "http://bridge.local:8775", "x" * 32)
    enrollment = await client.start_ring_enrollment("owner@example.com", "synthetic")
    assert enrollment.next_step == "otp"
    assert session.requests[0][2]["headers"]["Authorization"] == f"Bearer {'x' * 32}"
    assert "api_token" not in session.requests[0][1]


@pytest.mark.asyncio
async def test_invalid_otp_uses_the_stable_redacted_error() -> None:
    session = FakeSession([response(422, {"error": "invalid_otp"})])
    client = BridgeClient(session, "http://bridge.local:8775", "x" * 32)
    with pytest.raises(InvalidOtpError):
        await client.verify_ring_enrollment("synthetic", "123456")


@pytest.mark.asyncio
async def test_snapshot_is_bounded_and_requires_jpeg() -> None:
    session = FakeSession([FakeResponse(200, b"jpeg", "image/jpeg")])
    client = BridgeClient(session, "http://bridge.local:8765", "x" * 32)
    assert await client.snapshot("front-door") == b"jpeg"


def test_stream_url_uses_basic_auth_without_mutating_base_url() -> None:
    client = BridgeClient(FakeSession([]), "http://[fd00::1]:8765", "token/value")
    assert client.stream_url("front-door") == (
        "http://homeassistant:token%2Fvalue@[fd00::1]:8765/v1/cameras/front-door/live.ts"
    )
    assert client.base_url == "http://[fd00::1]:8765"


@pytest.mark.parametrize(
    "value",
    ["ftp://bridge", "http://user:pass@bridge", "http://bridge/path", "http://bridge?q=1"],
)
def test_url_normalization_rejects_unsafe_shapes(value: str) -> None:
    with pytest.raises(ValueError):
        normalize_url(value)
