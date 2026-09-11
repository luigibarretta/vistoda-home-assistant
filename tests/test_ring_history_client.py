"""Client contract for Ring cloud history."""

import json

import pytest

from custom_components.media_bridge.client import BridgeClient


class Content:
    async def iter_chunked(self, _size):
        yield self.body


class Response:
    def __init__(self, payload):
        self.status = 200
        self.body = json.dumps(payload).encode()
        self.content = Content()
        self.content.body = self.body
        self.content_length = len(self.body)
        self.content_type = "application/json"

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None


class Session:
    def __init__(self, payload):
        self.response = Response(payload)
        self.requests = []

    async def request(self, method, url, **kwargs):
        self.requests.append((method, url, kwargs))
        return self.response


@pytest.mark.asyncio
async def test_ring_history_is_server_paginated_and_identity_is_bounded() -> None:
    session = Session(
        {
            "identity": {
                "device_name": "Front Entrance",
                "location_name": "Home",
                "city": "Casoria",
                "device_id": "42",
            },
            "events": [
                {"event_id": "event-1", "event_type": "unlock", "occurred_at": 1_788_995_400}
            ],
            "next_cursor": "7323267080901445808",
        }
    )
    client = BridgeClient(session, "http://bridge.local:8775", "x" * 32)
    page = await client.ring_history(
        "front entrance",
        20,
        "7330963245622279024",
        expected_device_id="42",
    )
    assert page.identity.device_name == "Front Entrance"
    assert page.identity.location_name == "Home"
    assert page.identity.city == "Casoria"
    assert page.events[0].event_type == "unlock"
    assert page.next_cursor == "7323267080901445808"
    assert session.requests[0][1].endswith("/v1/devices/front%20entrance/history")
    assert session.requests[0][2]["params"] == {
        "limit": 20,
        "expected_device_id": "42",
        "cursor": "7330963245622279024",
    }
