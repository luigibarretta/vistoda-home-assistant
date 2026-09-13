"""Native camera routes retain exact identities and never use Intercom aliases."""

from unittest.mock import AsyncMock

import pytest

from custom_components.media_bridge import client_ring_camera as camera
from custom_components.media_bridge.client import BridgeClient
from custom_components.media_bridge.errors import CannotConnectError


def client(items):
    result = BridgeClient(None, "http://bridge.local:8787", "x" * 32)
    result._json = AsyncMock(return_value={"cameras": items})
    result._empty = AsyncMock()
    return result


def device(identity="18446744073709551615"):
    return {
        "device_id": identity,
        "name": "Front camera",
        "capabilities": {"available": ["live_video_receive"], "phase": "protocol_research"},
    }


async def test_inventory_exact_ids_and_no_vendor_secrets():
    bridge = client([{**device(), "vendor_token": "not-public"}])
    result = await camera.cameras(bridge)
    assert result[0]["device_id"] == "18446744073709551615"
    assert "vendor_token" not in result[0]
    bridge._json.assert_awaited_once_with("GET", "/v1/cameras")
    assert await camera.cameras(client([])) == []


@pytest.mark.parametrize(
    "items",
    [
        [device(123)],
        [device("../2")],
        [device(), device()],
        [{**device(), "capabilities": []}],
        [device()] * 129,
    ],
)
async def test_inventory_rejects_ambiguous_and_malformed_data(items):
    with pytest.raises(CannotConnectError):
        await camera.cameras(client(items))


async def test_stop_pins_camera_without_alias_or_unlock():
    bridge = client([])
    await camera.stop(bridge, "123", "session-1")
    bridge._empty.assert_awaited_once_with(
        "DELETE",
        "/v1/cameras/123/video/sessions/session-1",
        params={"expected_device_id": "123", "reason": "user_stop"},
    )
    with pytest.raises(CannotConnectError):
        await camera.stop(bridge, "123", "../2")
