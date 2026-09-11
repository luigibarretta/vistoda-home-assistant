"""Input and output validation for the provider-neutral client."""

import pytest

from custom_components.media_bridge.client_helpers import normalize_url
from custom_components.media_bridge.errors import CannotConnectError
from custom_components.media_bridge.models import parse_audio_session


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
