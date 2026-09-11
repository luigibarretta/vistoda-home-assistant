"""Native Ring cursor client tests kept separate for the LOC budget."""

import pytest

from custom_components.media_bridge.client import BridgeClient
from custom_components.media_bridge.client_ring_events import (
    RingEventCursor,
    RingPushBatch,
    RingPushEvent,
)
from custom_components.media_bridge.errors import CannotConnectError
from tests.test_client import FakeSession, response


@pytest.mark.asyncio
async def test_native_ring_events_use_a_bounded_cursor() -> None:
    session = FakeSession(
        [
            response(
                200,
                {
                    "events": [{"sequence": 8, "event_type": "ding", "occurred_at": 1787600000}],
                    "next_sequence": 8,
                    "generation": "00000000-0000-4000-8000-000000000001",
                    "connected": True,
                    "device_id": "42",
                    "cursor_reset": False,
                },
            )
        ]
    )
    client = BridgeClient(session, "http://bridge.local:8775", "x" * 32)
    batch = await client.ring_events(
        "entrance",
        7,
        expected_device_id="42",
        generation="00000000-0000-4000-8000-000000000001",
    )
    assert batch.events[0].event_type == "ding"
    assert batch.next_sequence == 8
    assert session.requests[0][2]["params"] == {
        "after": 7,
        "wait": 25,
        "expected_device_id": "42",
        "generation": "00000000-0000-4000-8000-000000000001",
    }


@pytest.mark.asyncio
async def test_native_ring_bootstrap_tails_without_replay() -> None:
    session = FakeSession(
        [
            response(
                200,
                {
                    "events": [],
                    "next_sequence": 12,
                    "generation": "00000000-0000-4000-8000-000000000001",
                    "connected": True,
                    "device_id": "42",
                    "cursor_reset": False,
                },
            )
        ]
    )
    client = BridgeClient(session, "http://bridge.local:8775", "x" * 32)
    batch = await client.ring_events("entrance", None, wait=0, expected_device_id="42")
    assert batch.next_sequence == 12
    assert session.requests[0][2]["params"] == {
        "wait": 0,
        "expected_device_id": "42",
    }


def test_event_cursor_resets_on_bridge_generation_without_replay() -> None:
    first = RingPushBatch((), 12, "00000000-0000-4000-8000-000000000001", True)
    current = RingPushBatch(
        (RingPushEvent(13, "ding", 1),),
        13,
        "00000000-0000-4000-8000-000000000001",
        True,
    )
    restarted = RingPushBatch(
        (RingPushEvent(1, "ding", 2),),
        1,
        "00000000-0000-4000-8000-000000000002",
        True,
    )
    cursor = RingEventCursor()
    assert cursor.consume(first) == ()
    assert cursor.consume(current) == current.events
    assert cursor.consume(restarted) == ()
    assert cursor.after == 1


def test_event_cursor_does_not_suppress_a_new_generation_with_a_high_old_cursor() -> None:
    cursor = RingEventCursor(
        after=100,
        generation="00000000-0000-4000-8000-000000000001",
    )
    restarted = RingPushBatch(
        (RingPushEvent(1, "ding", 2),),
        1,
        "00000000-0000-4000-8000-000000000002",
        True,
        "42",
        True,
    )
    assert cursor.consume(restarted) == restarted.events
    assert cursor.after == 1


@pytest.mark.asyncio
async def test_native_ring_events_reject_a_different_physical_device() -> None:
    session = FakeSession(
        [
            response(
                200,
                {
                    "events": [],
                    "next_sequence": 0,
                    "generation": "00000000-0000-4000-8000-000000000001",
                    "connected": True,
                    "device_id": "43",
                    "cursor_reset": False,
                },
            )
        ]
    )
    client = BridgeClient(session, "http://bridge.local:8775", "x" * 32)
    with pytest.raises(CannotConnectError):
        await client.ring_events("entrance", None, wait=0, expected_device_id="42")
