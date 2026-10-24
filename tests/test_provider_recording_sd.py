"""microSD intervals and not-yet-written manifests through the archive client."""

import pytest
from test_provider_recording_client import FakeSession

from custom_components.media_bridge.client import BridgeClient
from custom_components.media_bridge.errors import CannotConnectError

PENDING = {
    "recording_id": "00000000-0000-4000-8000-000000000002",
    "camera": "front",
    "status": "pending",
    "requested_at": "2026-10-24T06:00:00Z",
    "requested_duration_seconds": 30,
    "media_type": "application/octet-stream",
}


@pytest.mark.parametrize("status", ["pending", "recording", "failed"])
def test_unwritten_recordings_are_listed_not_rejected(status):
    # The bridge types the media only once written; a pending or failed item
    # used to make the whole archive list unavailable.
    item = BridgeClient._recording({**PENDING, "status": status})
    assert item["media_type"] == "application/octet-stream"


def test_a_ready_recording_still_needs_a_media_container():
    with pytest.raises(CannotConnectError):
        BridgeClient._recording({**PENDING, "status": "ready"})


def test_microsd_bounds_and_failure_codes_are_kept():
    item = BridgeClient._recording(
        {
            **PENDING,
            "status": "failed",
            "source": "sd",
            "sd_start": 10,
            "sd_end": 40,
            "error_code": "sd_no_recording",
        }
    )
    assert (item["source"], item["sd_start"], item["sd_end"]) == ("sd", 10, 40)
    assert item["error_code"] == "sd_no_recording"
    stripped = BridgeClient._recording({**PENDING, "source": "sd", "sd_start": "10"})
    assert "source" not in stripped


async def test_a_microsd_interval_is_requested_with_its_idempotency_key():
    session = FakeSession({**PENDING, "source": "sd", "sd_start": 1000, "sd_end": 1030})
    client = BridgeClient(session, "http://bridge.local:8765", "x" * 32)
    request_id = "00000000-0000-4000-8000-0000000000aa"
    result = await client.create_provider_sd_recording("front", (1000, 1030), request_id)
    method, url, options = session.last_request
    assert method == "POST" and url.endswith("/v1/cameras/front/recordings")
    assert options["json"] == {"source": "sd", "start": 1000, "end": 1030}
    assert options["headers"]["Idempotency-Key"] == request_id
    assert result["sd_start"] == 1000
