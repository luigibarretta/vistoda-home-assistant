"""The native push repair waits out self-healing registration rotations."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from custom_components.media_bridge.client_ring_events import RingPushBatch
from custom_components.media_bridge.errors import CannotConnectError
from tests.test_ring_reauth_push_health import batch, listener_env

GENERATION = "00000000-0000-4000-8000-000000000001"


def disconnected() -> RingPushBatch:
    return RingPushBatch((), 3, GENERATION, False, "42", False)


def outage_env(monkeypatch, responses, clock):
    env = listener_env(monkeypatch, [*responses, asyncio.CancelledError])
    # Replace only the listener's clock; the event loop keeps the real one.
    monkeypatch.setattr(env.module, "time", SimpleNamespace(monotonic=lambda: clock.pop(0)))
    env.listener._handle_push_health = AsyncMock()
    return env


def created_ids(env) -> list[str]:
    return [call.args[2] for call in env.issues.async_create_issue.call_args_list]


async def run(env) -> None:
    with pytest.raises(asyncio.CancelledError):
        await env.listener._run()


async def test_short_rotation_recovers_without_a_repair(monkeypatch) -> None:
    # Six disconnected polls over ~2.5 minutes, as on 2026-10-20 at 00:42.
    clock = [0, 25, 50, 75, 100, 150]
    env = outage_env(monkeypatch, [disconnected()] * 6 + [batch()], clock)
    await run(env)
    env.issues.async_create_issue.assert_not_called()
    assert env.listener._down_since is None
    assert env.issues.async_delete_issue.call_args.args[2] == "ring_push_unavailable_entry-1"


async def test_continuous_outage_raises_the_repair_after_the_grace(monkeypatch) -> None:
    grace = 900
    clock = [0, grace - 1, grace]
    env = outage_env(monkeypatch, [disconnected()] * 3, clock)
    await run(env)
    assert created_ids(env) == ["ring_push_unavailable_entry-1"]
    assert grace == env.module.PUSH_OUTAGE_GRACE_SECONDS


async def test_bridge_errors_share_the_same_outage_clock(monkeypatch) -> None:
    env = outage_env(monkeypatch, [CannotConnectError, disconnected()], [0, 899])
    await run(env)
    env.issues.async_create_issue.assert_not_called()
    assert env.listener._down_since == 0
