"""Contract tests for the bounded provider-neutral client."""

import json

import pytest

from custom_components.media_bridge.client import BridgeClient, normalize_url, parse_audio_session
from custom_components.media_bridge.errors import CannotConnectError, InvalidOtpError


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

    def ws_connect(self, url, **kwargs):
        self.requests.append(("WS", url, kwargs))
        return "synthetic-websocket-context"


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
        await client.verify_enrollment("synthetic", "123456")


@pytest.mark.asyncio
async def test_ezviz_enrollment_keeps_credentials_out_of_the_url() -> None:
    session = FakeSession(
        [response(200, {"enrollment_id": "synthetic", "next_step": "otp", "expires_in": 120})]
    )
    client = BridgeClient(session, "http://bridge.local:8765", "x" * 32)
    enrollment = await client.start_ezviz_enrollment("owner@example.com", "synthetic", "eu")
    assert enrollment.next_step == "otp"
    method, url, options = session.requests[0]
    assert method == "POST"
    assert url.endswith("/v1/enrollments")
    assert options["json"]["api_region"] == "eu"
    assert "owner@example.com" not in url
    assert "synthetic" not in url


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


@pytest.mark.asyncio
async def test_ring_audio_session_is_bounded_and_token_stays_in_header() -> None:
    session = FakeSession(
        [
            response(
                201,
                {
                    "session_id": "synthetic",
                    "answer_sdp": "v=0\r\nm=audio 9 RTP/AVP 0\r\na=sendrecv\r\n",
                    "ice_candidates": [{"candidate": "candidate:synthetic", "sdp_mline_index": 0}],
                    "expires_in": 120,
                },
            )
        ]
    )
    client = BridgeClient(session, "http://bridge.local:8775", "x" * 32)
    negotiated = await client.start_ring_audio("entrance", "v=0", "listen", 253)
    assert negotiated.session_id == "synthetic"
    assert session.requests[0][1].endswith("/v1/devices/entrance/audio/sessions")
    assert session.requests[0][2]["headers"]["Authorization"] == f"Bearer {'x' * 32}"
    assert session.requests[0][2]["json"]["ice_gathering_ms"] == 253
    assert "x" * 32 not in session.requests[0][1]


@pytest.mark.asyncio
async def test_ring_audio_stop_is_idempotent_at_bridge_contract() -> None:
    session = FakeSession([FakeResponse(204, b"")])
    client = BridgeClient(session, "http://bridge.local:8775", "x" * 32)
    await client.stop_ring_audio("entrance", "synthetic", "user_stop")
    assert session.requests[0][0] == "DELETE"
    assert session.requests[0][2]["params"] == {"reason": "user_stop"}


def test_native_ring_relay_is_private_bounded_and_uses_websocket_scheme() -> None:
    session = FakeSession([])
    client = BridgeClient(session, "https://[fd00::1]:8775", "x" * 32)
    context = client.ring_relay("front entrance")
    assert context == "synthetic-websocket-context"
    method, url, options = session.requests[0]
    assert method == "WS"
    assert url == "wss://[fd00::1]:8775/v1/devices/front%20entrance/audio/relay"
    assert options["headers"]["Authorization"] == f"Bearer {'x' * 32}"
    assert options["max_msg_size"] == 2048


@pytest.mark.asyncio
async def test_native_ring_status_and_controls_are_bounded() -> None:
    session = FakeSession(
        [
            response(
                200,
                {
                    "battery": 73,
                    "online": True,
                    "doorbell_volume": 6,
                    "mic_volume": 10,
                    "voice_volume": 9,
                    "last_activity": 1786800000,
                },
            ),
            FakeResponse(204, b""),
            FakeResponse(204, b""),
        ]
    )
    client = BridgeClient(session, "http://bridge.local:8775", "x" * 32)
    status = await client.ring_status("entrance")
    assert status.battery == 73
    assert status.online is True
    await client.set_ring_volume("entrance", "mic_volume", 10)
    await client.unlock_ring("entrance")
    assert session.requests[1][0:2] == (
        "PATCH",
        "http://bridge.local:8775/v1/devices/entrance/settings",
    )
    assert session.requests[1][2]["json"] == {"mic_volume": 10}
    assert session.requests[2][0] == "POST"


@pytest.mark.asyncio
async def test_local_ring_recording_upload_and_inventory_are_private() -> None:
    session = FakeSession(
        [
            response(
                201,
                {
                    "recording_id": "recording-1",
                    "started_at": 1786800000,
                    "ended_at": 1786800010,
                    "saved_at": 1786800011,
                    "bytes": 2048,
                    "media_type": "audio/webm",
                },
            ),
            response(
                200,
                {
                    "recordings": [
                        {
                            "recording_id": "recording-1",
                            "started_at": 1786799990,
                            "ended_at": 1786800000,
                            "saved_at": 1786800010,
                            "bytes": 2048,
                            "media_type": "audio/webm",
                        }
                    ]
                },
            ),
        ]
    )
    client = BridgeClient(session, "http://bridge.local:8775", "x" * 32)
    saved = await client.upload_ring_recording(
        "entrance", 1786800000, 1786800010, "audio/webm;codecs=opus", b"x" * 2048
    )
    assert saved.recording_id == "recording-1"
    recordings = await client.ring_recordings("entrance")
    assert recordings[0].bytes == 2048
    assert session.requests[0][2]["headers"]["Content-Type"] == "audio/webm;codecs=opus"
    assert session.requests[0][2]["params"] == {
        "started_at": 1786800000,
        "ended_at": 1786800010,
    }
    assert all(
        request[2]["headers"]["Authorization"].startswith("Bearer ") for request in session.requests
    )
    assert all("x" * 32 not in request[1] for request in session.requests)


def test_ring_audio_response_rejects_oversized_candidate_sets() -> None:
    with pytest.raises(CannotConnectError):
        parse_audio_session(
            {
                "session_id": "synthetic",
                "answer_sdp": "v=0\r\n",
                "ice_candidates": [
                    {"candidate": f"candidate:{index}", "sdp_mline_index": 0} for index in range(65)
                ],
                "expires_in": 120,
            }
        )


@pytest.mark.parametrize(
    "value",
    ["ftp://bridge", "http://user:pass@bridge", "http://bridge/path", "http://bridge?q=1"],
)
def test_url_normalization_rejects_unsafe_shapes(value: str) -> None:
    with pytest.raises(ValueError):
        normalize_url(value)
