"""Revoked Ring sessions, push silence repairs and missed-call bus events."""

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from ha_stub_support import AuthFailedError, UpdateFailedError, config_entry, load, stub_ha

from custom_components.media_bridge.client import BridgeClient
from custom_components.media_bridge.client_ring_events import RingPushBatch
from custom_components.media_bridge.errors import (
    BridgeError,
    CannotConnectError,
    InvalidBridgeAuthError,
    ReauthRequiredError,
)
from tests.test_client import FakeResponse, FakeSession, response

GENERATION = "00000000-0000-4000-8000-000000000001"


def batch_payload(**extra) -> dict:
    return {
        "events": [],
        "next_sequence": 3,
        "generation": GENERATION,
        "connected": True,
        "device_id": "42",
        "cursor_reset": False,
        **extra,
    }


@pytest.mark.parametrize(
    ("status", "body", "error"),
    [
        (403, {"error": "reauth_required"}, ReauthRequiredError),
        (403, {"error": "forbidden"}, CannotConnectError),
        (401, {"error": "reauth_required"}, InvalidBridgeAuthError),
    ],
)
async def test_revoked_ring_session_maps_only_403_reauth_required(status, body, error) -> None:
    session = FakeSession([FakeResponse(status, json.dumps(body).encode())])
    client = BridgeClient(session, "http://bridge.local:8775", "x" * 32)
    with pytest.raises(error):
        await client.ring_status("entrance")
    assert issubclass(ReauthRequiredError, BridgeError)


async def test_optional_push_hints_parse_and_stay_backward_compatible() -> None:
    payloads = [
        batch_payload(),
        batch_payload(push_degraded=True, last_missed_ding_at=1787600000),
        batch_payload(push_degraded="yes", last_missed_ding_at=True),
        batch_payload(push_degraded=False, last_missed_ding_at=-1),
    ]
    client = BridgeClient(
        FakeSession([response(200, item) for item in payloads]), "http://b.local", "x" * 32
    )
    results = [
        await client.ring_events("entrance", 2, expected_device_id="42", generation=GENERATION)
        for _ in payloads
    ]
    assert [(item.push_degraded, item.last_missed_ding_at) for item in results] == [
        (None, None),
        (True, 1787600000),
        (None, None),
        (False, None),
    ]


async def test_status_coordinator_turns_revoked_session_into_reauth(monkeypatch) -> None:
    stub_ha(monkeypatch)
    module = load(monkeypatch, "ring_status")
    entry = config_entry()
    client = SimpleNamespace(ring_status=AsyncMock(side_effect=ReauthRequiredError))
    coordinator = module.RingStatusCoordinator(SimpleNamespace(), client, "entrance", entry)
    assert coordinator.config_entry is entry
    with pytest.raises(AuthFailedError):
        await coordinator._async_update_data()
    client.ring_status.side_effect = CannotConnectError
    with pytest.raises(UpdateFailedError):
        await coordinator._async_update_data()


def listener_env(monkeypatch, responses):
    issues = stub_ha(monkeypatch)
    load(monkeypatch, "repairs")
    module = load(monkeypatch, "ring_event_listener")
    sleeps = []

    async def sleep(seconds):
        sleeps.append(seconds)
        if len(sleeps) >= 3:
            raise asyncio.CancelledError

    monkeypatch.setattr(module.asyncio, "sleep", sleep)
    entry = config_entry(ring_device_id="42")
    client = SimpleNamespace(ring_events=AsyncMock(side_effect=responses))
    history = SimpleNamespace(async_record=AsyncMock())
    listener = module.RingEventListener(SimpleNamespace(), entry, client, "entrance", history)
    return SimpleNamespace(
        module=module, issues=issues, sleeps=sleeps, entry=entry, listener=listener
    )


async def test_revoked_session_starts_reauth_once_without_push_outage(monkeypatch) -> None:
    env = listener_env(monkeypatch, [ReauthRequiredError] * 3)
    with pytest.raises(asyncio.CancelledError):
        await env.listener._run()
    env.entry.async_start_reauth.assert_called_once()
    assert env.sleeps == [env.module.REAUTH_RETRY_SECONDS] * 3
    assert env.listener.reauth_required and not env.listener.connected
    env.issues.async_create_issue.assert_not_called()


def batch(**hints) -> RingPushBatch:
    return RingPushBatch((), 3, GENERATION, True, "42", False, **hints)


async def test_push_silence_issue_follows_engine_hint(monkeypatch) -> None:
    env = listener_env(monkeypatch, [])
    await env.listener._handle_push_health(batch())
    env.issues.async_create_issue.assert_not_called()
    env.issues.async_delete_issue.assert_not_called()
    await env.listener._handle_push_health(batch(push_degraded=True))
    args = env.issues.async_create_issue.call_args
    assert args.args[2] == "ring_push_silent_entry-1"
    assert args.kwargs["translation_key"] == "ring_push_silent"
    assert args.kwargs["translation_placeholders"] == {"name": "Front door"}
    await env.listener._handle_push_health(batch(push_degraded=False))
    assert env.issues.async_delete_issue.call_args.args[2] == "ring_push_silent_entry-1"


async def test_listener_publishes_missed_call_from_batch(monkeypatch) -> None:
    env = listener_env(monkeypatch, [])
    publish = AsyncMock()
    monkeypatch.setattr(env.module, "async_publish_missed_call", publish)
    await env.listener._handle_push_health(batch(last_missed_ding_at=1787600000))
    publish.assert_awaited_once_with(env.listener.history, 1787600000)


class FakeHistory:
    def __init__(self, stored=None) -> None:
        self.hass = SimpleNamespace(bus=SimpleNamespace(async_fire=Mock()))
        self.entry = SimpleNamespace(entry_id="entry-1")
        self.alias = "entrance"
        self.identity = {"device_name": "Portone", "location_name": "Casa", "city": ""}
        self._lock = asyncio.Lock()
        self._data = {} if stored is None else {"last_missed_ding_at": stored}
        self._store = SimpleNamespace(async_save=AsyncMock())

    async def _async_load(self) -> None:
        return None


async def test_missed_call_event_fires_once_per_new_timestamp() -> None:
    from custom_components.media_bridge.ring_missed_call import (
        EVENT_RING_MISSED_CALL,
        async_publish_missed_call,
    )

    history = FakeHistory()
    assert await async_publish_missed_call(history, 1000, now=1100)
    assert not await async_publish_missed_call(history, 1000, now=1200)
    assert not await async_publish_missed_call(history, 900, now=1200)
    assert await async_publish_missed_call(history, 5000, now=5000)
    fired = history.hass.bus.async_fire.call_args_list
    assert [call.args[0] for call in fired] == [EVENT_RING_MISSED_CALL] * 2
    assert fired[0].args[1] == {
        "device_name": "Portone",
        "location_name": "Casa",
        "city": "",
        "entry_id": "entry-1",
        "alias": "entrance",
        "occurred_at": 1000,
    }
    assert history._data["last_missed_ding_at"] == 5000


async def test_first_seen_old_missed_call_becomes_silent_baseline() -> None:
    from custom_components.media_bridge.ring_missed_call import async_publish_missed_call

    history = FakeHistory()
    assert not await async_publish_missed_call(history, 1000, now=1000 + 86400)
    assert history._data["last_missed_ding_at"] == 1000
    history.hass.bus.async_fire.assert_not_called()
    restarted = FakeHistory(stored=1000)
    assert not await async_publish_missed_call(restarted, 1000, now=1000)
    assert await async_publish_missed_call(restarted, 1001, now=1000 + 86400)
