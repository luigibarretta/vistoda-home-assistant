"""Executable native camera ownership, caps and teardown tests; no provider I/O."""

import asyncio

import pytest
from ring_camera_ws_support import boundary, connection, message

from custom_components.media_bridge.errors import CannotConnectError


@pytest.mark.parametrize("handler", ["inventory", "create", "delete"])
async def test_non_admin_cannot_reach_inventory_or_media(monkeypatch, handler):
    env = boundary(monkeypatch)
    owner = connection(admin=False)
    with pytest.raises(PermissionError):
        await getattr(env.api, handler)(env.hass, owner, message())
    env.api.resolve.assert_not_called()
    env.api.camera.cameras.assert_not_awaited()
    env.api.camera.start.assert_not_awaited()
    env.api.camera.stop.assert_not_awaited()
    assert not env.hass.data and not owner.subscriptions


async def test_inventory_registers_all_handlers_without_starting_media(monkeypatch):
    env = boundary(monkeypatch)
    env.api.async_register(env.hass)
    assert env.registration.call_count == 3
    owner = connection()
    await env.api.inventory(env.hass, owner, message())
    owner.send_result.assert_called_once_with(1, {"cameras": []})
    env.api.camera.start.assert_not_awaited()
    assert not env.hass.data


async def test_delete_requires_same_connection_entry_camera_and_session(monkeypatch):
    env = boundary(monkeypatch)
    owner = connection()
    await env.api.create(env.hass, owner, message())
    assert env.timers[0].delay == 120
    for actor, msg in [
        (connection(), message(2)),
        (owner, message(2, entry="other")),
        (owner, message(2, camera="52")),
        (owner, message(2, session="other-session")),
    ]:
        await env.api.delete(env.hass, actor, msg)
    env.api.camera.stop.assert_not_awaited()
    assert len(env.hass.data[env.api.LEDGER]) == 1
    await env.api.delete(env.hass, owner, message(3))
    await env.api.delete(env.hass, owner, message(4))
    env.api.camera.stop.assert_awaited_once_with(env.client, "51", "synthetic-session")
    assert env.timers[0].cancelled
    assert not owner.subscriptions and not env.hass.data[env.api.LEDGER]


@pytest.mark.parametrize("trigger", ["disconnect", "expiry", "unload"])
async def test_active_cleanup_stops_exact_session_once(monkeypatch, trigger):
    env = boundary(monkeypatch)
    owner = connection()
    await env.api.create(env.hass, owner, message())
    if trigger == "disconnect":
        for cleanup in list(owner.subscriptions.values()):
            cleanup()
    elif trigger == "expiry":
        env.timers[0].callback()
    else:
        await env.api.async_close_entry(env.hass, "account")
    await env.drain()
    # A queued timer or repeated unload cannot issue a second provider DELETE.
    env.timers[0].callback()
    await env.api.async_close_entry(env.hass, "account")
    await env.drain()
    env.api.camera.stop.assert_awaited_once_with(env.client, "51", "synthetic-session")
    assert not env.hass.data[env.api.LEDGER] and not owner.subscriptions


@pytest.mark.parametrize("trigger", ["disconnect", "unload"])
async def test_pending_close_deletes_late_provider_result_without_delivering_it(
    monkeypatch, trigger
):
    env = boundary(monkeypatch)
    entered, release = asyncio.Event(), asyncio.Event()

    async def pending(*_):
        entered.set()
        await release.wait()
        return env.result

    env.api.camera.start.side_effect = pending
    owner = connection()
    task = asyncio.create_task(env.api.create(env.hass, owner, message()))
    await asyncio.wait_for(entered.wait(), 1)
    if trigger == "disconnect":
        for cleanup in list(owner.subscriptions.values()):
            cleanup()
        owner.subscriptions.clear()  # Core clears subscriptions after disconnect callbacks.
    else:
        await env.api.async_close_entry(env.hass, "account")
    assert not env.hass.data[env.api.LEDGER]
    release.set()
    await task
    env.api.camera.stop.assert_awaited_once_with(env.client, "51", "synthetic-session")
    owner.send_result.assert_not_called()
    assert not env.timers and not owner.subscriptions


async def test_pending_requests_count_towards_owner_and_global_caps(monkeypatch):
    env = boundary(monkeypatch)
    release, all_entered = asyncio.Event(), asyncio.Event()
    count = 0

    async def pending(*_):
        nonlocal count
        count += 1
        if count == 8:
            all_entered.set()
        await release.wait()
        return env.result

    env.api.camera.start.side_effect = pending
    owners = [connection() for _ in range(9)]
    tasks = [
        asyncio.create_task(env.api.create(env.hass, owner, message(index + 1)))
        for index, owner in enumerate(owners[:8])
    ]
    await asyncio.wait_for(all_entered.wait(), 1)
    for owner in (owners[0], owners[8]):
        await env.api.create(env.hass, owner, message(20))
        assert owner.send_error.call_args.args[1] == "session_busy"
    assert env.api.camera.start.await_count == 8
    release.set()
    await asyncio.gather(*tasks)
    await env.api.async_close_entry(env.hass, "account")
    assert env.api.camera.stop.await_count == 8
    assert not env.hass.data[env.api.LEDGER]
    assert all(not owner.subscriptions for owner in owners)


async def test_one_owner_cannot_start_a_second_camera_while_first_is_pending(monkeypatch):
    env = boundary(monkeypatch)
    entered, release = asyncio.Event(), asyncio.Event()

    async def pending(*_):
        entered.set()
        await release.wait()
        return env.result

    env.api.camera.start.side_effect = pending
    owner = connection()
    task = asyncio.create_task(env.api.create(env.hass, owner, message()))
    await asyncio.wait_for(entered.wait(), 1)
    await env.api.create(env.hass, owner, message(2, camera="52"))
    assert owner.send_error.call_args.args[1] == "session_busy"
    env.api.camera.start.assert_awaited_once()
    release.set()
    await task
    await env.api.async_close_entry(env.hass, "account")


async def test_provider_failure_and_cancellation_release_pending_reservations(monkeypatch):
    env = boundary(monkeypatch)
    owner = connection()
    env.api.camera.start.side_effect = CannotConnectError
    await env.api.create(env.hass, owner, message())
    assert owner.send_error.call_args.args[1] == "unavailable"
    assert not owner.subscriptions and not env.hass.data[env.api.LEDGER]
    env.api.camera.start.side_effect = asyncio.CancelledError
    with pytest.raises(asyncio.CancelledError):
        await env.api.create(env.hass, owner, message(2))
    assert not owner.subscriptions and not env.hass.data[env.api.LEDGER]
    env.api.camera.stop.assert_not_awaited()


async def test_entry_unload_keeps_other_account_session(monkeypatch):
    env = boundary(monkeypatch)
    first, second = connection(), connection()
    await env.api.create(env.hass, first, message())
    await env.api.create(env.hass, second, message(2, entry="other", camera="52"))
    await env.api.async_close_entry(env.hass, "account")
    assert not first.subscriptions and second.subscriptions
    assert len(env.hass.data[env.api.LEDGER]) == 1
    env.api.camera.stop.assert_awaited_once_with(env.client, "51", "synthetic-session")
    await env.api.async_close_entry(env.hass, "other")
    assert not second.subscriptions and not env.hass.data[env.api.LEDGER]


async def test_failed_provider_stop_still_clears_local_lease(monkeypatch):
    env = boundary(monkeypatch)
    owner = connection()
    await env.api.create(env.hass, owner, message())
    env.api.camera.stop.side_effect = CannotConnectError
    await env.api.delete(env.hass, owner, message(2))
    assert not owner.subscriptions and not env.hass.data[env.api.LEDGER]
    assert env.timers[0].cancelled
