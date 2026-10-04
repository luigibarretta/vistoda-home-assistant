"""EZVIZ alarm cursor, parsing and picture client contract."""

import pytest

from custom_components.media_bridge.client import BridgeClient
from custom_components.media_bridge.client_ezviz_alarms import (
    AlarmsUnsupportedError,
    EzvizAlarmBatch,
    EzvizAlarmCursor,
    alarm_picture_path,
    parse_alarm,
    parse_alarm_batch,
)
from custom_components.media_bridge.errors import CannotConnectError, InvalidBridgeAuthError
from tests.test_client import FakeResponse, FakeSession, response


def item(sequence: int, **extra) -> dict:
    return {
        "sequence": sequence,
        "id": f"alarm-{sequence}",
        "occurred_at": 1_790_000_000 + sequence,
        "alarm_type": 10000,
        "category": "person",
        "title": "Persona rilevata",
        "has_picture": True,
        **extra,
    }


def payload(events=(), next_sequence=5, generation="gen-a", camera="front-door") -> dict:
    return {
        "camera": camera,
        "generation": generation,
        "next_sequence": next_sequence,
        "events": list(events),
    }


def client(*responses) -> tuple[BridgeClient, FakeSession]:
    session = FakeSession(list(responses))
    return BridgeClient(session, "http://ezviz.local:8765", "x" * 32), session


async def test_history_omits_cursor_and_tail_long_polls() -> None:
    bridge, session = client(
        response(200, payload([item(4), item(5)])), response(200, payload([item(6)], 6))
    )
    history = await bridge.ezviz_alarms("front-door")
    assert [event.sequence for event in history.events] == [4, 5]
    assert session.requests[0][1] == "http://ezviz.local:8765/v1/cameras/front-door/alarms"
    assert session.requests[0][2]["params"] == {}
    assert session.requests[0][2]["headers"]["Authorization"] == f"Bearer {'x' * 32}"
    await bridge.ezviz_alarms("front-door", 5, wait=90)
    assert session.requests[1][2]["params"] == {"after": 5, "wait": 25}


async def test_old_app_404_is_a_distinct_unsupported_signal() -> None:
    bridge, _session = client(response(404, {"error": "not_found"}), response(401, {}))
    with pytest.raises(AlarmsUnsupportedError):
        await bridge.ezviz_alarms("front-door")
    with pytest.raises(InvalidBridgeAuthError):
        await bridge.ezviz_alarms("front-door", 3)


@pytest.mark.parametrize(
    "bad",
    [
        payload(camera="other-camera"),
        payload([item(6)], next_sequence=5),
        payload(generation=""),
        payload(generation=True),
        payload(next_sequence=-1),
        payload([item(2, id="a/b")]),
        payload([item(2, id="")]),
        payload([item(2, occurred_at="today")]),
        payload([{**item(2), "sequence": True}]),
        payload([item(n) for n in range(129)], next_sequence=200),
        {"camera": "front-door", "generation": "gen-a", "events": []},
    ],
)
def test_malformed_batches_fail_closed(bad) -> None:
    with pytest.raises(CannotConnectError):
        parse_alarm_batch(bad, "front-door")


def test_vendor_fields_are_normalized_without_rejecting_new_categories() -> None:
    alarm = parse_alarm(
        item(3, category="baby_cry", title="  Tag\x00 <b>x</b>\n" + "y" * 300, has_picture="yes")
    )
    assert alarm.category == "other"
    assert alarm.title.startswith("Tag <b>x</b> y") and len(alarm.title) == 160
    assert alarm.has_picture is False
    assert parse_alarm(item(1, generation=7)).alarm_id == "alarm-1"
    assert parse_alarm_batch(payload(generation=42), "front-door").generation == "42"


def test_picture_path_only_for_url_safe_ids_with_pictures() -> None:
    assert alarm_picture_path("01J9", parse_alarm(item(2))) == (
        "/api/media_bridge/ezviz/01J9/alarms/alarm-2.jpg"
    )
    assert alarm_picture_path("01J9", parse_alarm(item(2, has_picture=False))) is None
    assert alarm_picture_path("01J9", parse_alarm(item(2, id="a.b:c"))) is None


def batch(sequences, next_sequence, generation="gen-a") -> EzvizAlarmBatch:
    events = tuple(parse_alarm(item(sequence)) for sequence in sequences)
    return EzvizAlarmBatch(events, next_sequence, generation)


def test_cursor_primes_tails_and_never_replays() -> None:
    cursor = EzvizAlarmCursor()
    assert cursor.consume(batch([3, 4, 5], 5)) == ()
    assert cursor.after == 5
    assert [alarm.sequence for alarm in cursor.consume(batch([6, 7], 7))] == [6, 7]
    assert cursor.consume(batch([6, 7], 7)) == ()
    assert [alarm.sequence for alarm in cursor.consume(batch([7, 8], 8))] == [8]


def test_cursor_reprimes_on_generation_change_and_rewind() -> None:
    cursor = EzvizAlarmCursor()
    cursor.consume(batch([], 40))
    assert cursor.consume(batch([1, 2], 2, "gen-b")) == ()
    assert (cursor.after, cursor.generation) == (2, "gen-b")
    assert cursor.consume(batch([], 1, "gen-b")) == ()
    assert cursor.after == 1
    assert [alarm.sequence for alarm in cursor.consume(batch([2], 2, "gen-b"))] == [2]


async def test_picture_is_bounded_jpeg_and_404_means_none() -> None:
    jpeg = b"\xff\xd8\xff\xe0" + b"0" * 64
    bridge, session = client(
        FakeResponse(200, jpeg, "image/jpeg"),
        response(404, {}),
        FakeResponse(200, b"<html>", "text/html"),
    )
    assert await bridge.ezviz_alarm_picture("front-door", "alarm-1") == jpeg
    assert session.requests[0][1].endswith("/v1/cameras/front-door/alarms/alarm-1/picture.jpg")
    assert await bridge.ezviz_alarm_picture("front-door", "alarm-2") is None
    with pytest.raises(CannotConnectError):
        await bridge.ezviz_alarm_picture("front-door", "alarm-3")
    assert await bridge.ezviz_alarm_picture("front-door", "../snapshot") is None
    assert len(session.requests) == 3
