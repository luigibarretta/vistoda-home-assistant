"""SceneTrove microSD sync client: one bounded route, stable codes, no upstream text."""

import json

import pytest
from aiohttp import ClientError
from test_client import FakeResponse, FakeSession

from custom_components.media_bridge.scenetrove_sync import (
    SceneTroveSyncClient,
    SceneTroveSyncError,
    status_payload,
    sync_target,
    valid_schedule,
    verify_sync_token,
)

TOKEN = "scenetrove_pat_" + "a" * 43
STATUS = {
    "settings": {
        "enabled": True,
        "interval_minutes": 360,
        "days_back": 2,
        "max_clips_per_run": 20,
        "max_clip_seconds": 120,
        "backfill_from": None,
    },
    "available": True,
    "running": False,
    "last": {
        "trigger": "schedule",
        "started_at": "2026-11-19T20:48:05Z",
        "finished_at": "2026-11-19T20:48:06Z",
        "result": "bridge_error",
        "imported": 0,
        "skipped": 0,
        "failed": 1,
        "given_up": 2,
        "message": "HTTP 503 upstream_unavailable at /private/path",
        "backlog_days": 0,
    },
    "last_success_at": "2026-11-04T19:54:21Z",
    "next_run_at": "2026-11-20T02:48:06Z",
}


def client(session) -> SceneTroveSyncClient:
    return SceneTroveSyncClient(session, "https://st.example", "front door", TOKEN)


def ok(payload) -> FakeResponse:
    return FakeResponse(200, json.dumps(payload).encode())


async def test_status_uses_the_bearer_token_and_an_encoded_device() -> None:
    session = FakeSession([ok(STATUS)])
    sync = await client(session).status()
    method, url, kwargs = session.requests[0]
    assert (method, url) == ("GET", "https://st.example/api/devices/front%20door/sd-sync")
    assert kwargs["headers"] == {"Authorization": f"Bearer {TOKEN}"}
    assert sync == {
        "enabled": True,
        "interval_minutes": 360,
        "available": True,
        "running": False,
        "last": {
            "result": "bridge_error",
            "finished_at": "2026-11-19T20:48:06Z",
            "imported": 0,
            "failed": 3,
        },
        "last_success_at": "2026-11-04T19:54:21Z",
        "next_run_at": "2026-11-20T02:48:06Z",
    }
    assert "message" not in json.dumps(sync), "upstream free text never reaches the panel"


async def test_set_schedule_sends_only_enabled_and_interval() -> None:
    session = FakeSession([ok(STATUS)])
    await client(session).set_schedule(False, 720)
    method, _url, kwargs = session.requests[0]
    assert method == "PUT"
    assert kwargs["json"] == {"enabled": False, "interval_minutes": 720}
    assert kwargs["allow_redirects"] is False, "the token never follows a redirect"


async def test_a_put_404_after_a_working_get_means_an_older_scenetrove() -> None:
    def missing() -> FakeResponse:
        return FakeResponse(404, json.dumps({"error": "unknown_device"}).encode())

    session = FakeSession([missing(), ok(STATUS)])
    with pytest.raises(SceneTroveSyncError) as raised:
        await client(session).set_schedule(True, 360)
    assert raised.value.code == "scenetrove_unsupported_version"
    assert [request[0] for request in session.requests] == ["PUT", "GET"]
    # Both answering 404: the device really is unknown.
    session = FakeSession([missing(), missing()])
    with pytest.raises(SceneTroveSyncError) as raised:
        await client(session).set_schedule(True, 360)
    assert raised.value.code == "scenetrove_unknown_device"


@pytest.mark.parametrize(
    ("status", "body", "code"),
    [
        (401, {"error": "unauthorized"}, "scenetrove_unauthorized"),
        (403, {"error": "admin_required"}, "scenetrove_unauthorized"),
        (404, {"error": "unknown_device"}, "scenetrove_unknown_device"),
        (409, {"error": "live_source_required"}, "scenetrove_live_source_required"),
        (400, {"error": "invalid_sd_sync_interval"}, "scenetrove_rejected"),
        (502, {"error": "bad_gateway"}, "scenetrove_unavailable"),
        (302, {}, "scenetrove_redirected"),
        (307, {}, "scenetrove_redirected"),
    ],
)
async def test_errors_map_to_stable_codes(status, body, code) -> None:
    # Two answers: a PUT 404 is checked with a GET of the same device.
    answers = [FakeResponse(status, json.dumps(body).encode()) for _ in range(2)]
    with pytest.raises(SceneTroveSyncError) as raised:
        await client(FakeSession(answers)).set_schedule(True, 360)
    assert raised.value.code == code


async def test_oversized_invalid_and_unreachable_answers_fail_closed() -> None:
    for answer in (FakeResponse(200, b"x" * (17 * 1024)), FakeResponse(200, b"not json")):
        with pytest.raises(SceneTroveSyncError) as raised:
            await client(FakeSession([answer])).status()
        assert raised.value.code == "scenetrove_invalid_response"

    class Unreachable(FakeSession):
        async def request(self, method, url, **kwargs):
            raise ClientError("down")

    with pytest.raises(SceneTroveSyncError) as raised:
        await client(Unreachable([])).status()
    assert raised.value.code == "scenetrove_unreachable"


def test_status_payload_rejects_shapes_it_cannot_trust() -> None:
    for raw in (None, [], {"settings": None}, {"settings": {"enabled": "yes"}}):
        with pytest.raises(SceneTroveSyncError):
            status_payload(raw)
    odd = {**STATUS, "last": {**STATUS["last"], "result": "<script>"}, "next_run_at": None}
    payload = status_payload(odd)
    assert payload["last"]["result"] == "bridge_error"
    assert payload["next_run_at"] is None


def test_only_offered_intervals_and_real_booleans_are_valid() -> None:
    assert all(valid_schedule(True, minutes) for minutes in (60, 180, 360, 720, 1440))
    # Turning off sends back any interval SceneTrove accepts, custom ones included.
    assert all(valid_schedule(False, minutes) for minutes in (15, 30, 360, 1440))
    for minutes in (14, 1441, True, "60", 30.0):
        assert not valid_schedule(False, minutes), minutes
    for enabled, minutes in ((True, 15), (True, 1441), (True, True), (1, 60), (True, "60")):
        assert not valid_schedule(enabled, minutes), (enabled, minutes)


def test_target_needs_address_device_and_token() -> None:
    linked = {"scenetrove_url": "https://st.example", "scenetrove_device": "spioncino"}
    assert sync_target(linked) is None
    assert sync_target({**linked, "scenetrove_token": TOKEN}) == (
        "https://st.example",
        "spioncino",
        TOKEN,
    )
    assert sync_target({"scenetrove_token": TOKEN}) is None


@pytest.mark.parametrize(
    ("status", "error"),
    [
        (403, None),
        (200, "scenetrove_token_too_broad"),
        (401, "scenetrove_token_rejected"),
        (302, "scenetrove_token_unverified"),
        (404, "scenetrove_token_unverified"),
        (500, "scenetrove_token_unverified"),
    ],
)
async def test_a_token_is_stored_only_when_scenetrove_refuses_it_the_device_list(
    status, error
) -> None:
    session = FakeSession([FakeResponse(status, b"{}")])
    assert await verify_sync_token(session, "https://st.example", TOKEN) == error
    method, url, kwargs = session.requests[0]
    assert (method, url) == ("GET", "https://st.example/api/devices")
    assert kwargs["headers"] == {"Authorization": f"Bearer {TOKEN}"}
    assert kwargs["allow_redirects"] is False


async def test_an_unreachable_scenetrove_cannot_verify_a_token() -> None:
    class Unreachable(FakeSession):
        async def request(self, method, url, **kwargs):
            raise TimeoutError

    assert (
        await verify_sync_token(Unreachable([]), "https://st.example", TOKEN)
        == "scenetrove_token_unverified"
    )
