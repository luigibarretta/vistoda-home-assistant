"""Outage repairs wait for a continuous 15-minute outage; real problems are immediate."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from ha_stub_support import AuthFailedError, UpdateFailedError, config_entry, load, stub_ha

from custom_components.media_bridge import outage
from custom_components.media_bridge.errors import CannotConnectError, ReauthRequiredError

SOURCE = "SERIAL1:1"


def env(monkeypatch, clock, provider="ring", **data):
    issues = stub_ha(monkeypatch)
    load(monkeypatch, "repairs")
    module = load(monkeypatch, "coordinator")
    monkeypatch.setattr(outage, "time", SimpleNamespace(monotonic=lambda: clock.pop(0)))
    entry = config_entry(provider, **data)
    client = SimpleNamespace(
        health=AsyncMock(return_value=SimpleNamespace(version="1.0")),
        ezviz_camera_identity=AsyncMock(return_value=SOURCE),
    )
    # Not running: the native EZVIZ dependency check stays out of these tests.
    hass = SimpleNamespace(is_running=False)
    coordinator = module.BridgeCoordinator(hass, client, entry, "Vistoda bridge")
    return SimpleNamespace(
        module=module, issues=issues, entry=entry, client=client, coordinator=coordinator
    )


def created(env) -> list[tuple[str, str, str]]:
    return [
        (call.args[2], call.kwargs["translation_key"], call.kwargs["severity"])
        for call in env.issues.async_create_issue.call_args_list
    ]


def deleted(env) -> list[str]:
    return [call.args[2] for call in env.issues.async_delete_issue.call_args_list]


async def poll(env, error=UpdateFailedError):
    with pytest.raises(error):
        await env.coordinator._async_update_data()


async def test_bridge_repair_waits_for_a_continuous_outage(monkeypatch) -> None:
    test = env(monkeypatch, [0, 60, 899, 900])
    assert test.coordinator.config_entry is test.entry
    test.client.health.side_effect = CannotConnectError
    for _ in range(3):
        await poll(test)
    assert created(test) == []
    await poll(test)
    assert created(test) == [("bridge_unavailable_entry-1", "bridge_unavailable", "warning")]


async def test_one_success_clears_the_repair_and_restarts_the_clock(monkeypatch) -> None:
    test = env(monkeypatch, [0, 900, 1000, 1000 + 899])
    test.client.health.side_effect = CannotConnectError
    await poll(test)
    await poll(test)
    test.client.health.side_effect = None
    assert await test.coordinator._async_update_data() == "1.0"
    assert deleted(test)[-1] == "bridge_unavailable_entry-1"
    test.client.health.side_effect = CannotConnectError
    await poll(test)
    await poll(test)
    # One repair for the first outage; the second one is still within its grace.
    assert len(created(test)) == 1


async def test_the_outage_survives_setup_retries(monkeypatch) -> None:
    # A failing first refresh makes Home Assistant recreate the coordinator.
    test = env(monkeypatch, [0, 900])
    test.client.health.side_effect = CannotConnectError
    await poll(test)
    retry = test.module.BridgeCoordinator(
        test.coordinator.hass, test.client, test.entry, "Vistoda bridge"
    )
    with pytest.raises(UpdateFailedError):
        await retry._async_update_data()
    assert [item[0] for item in created(test)] == ["bridge_unavailable_entry-1"]


async def test_changed_ezviz_camera_is_reported_at_once(monkeypatch) -> None:
    test = env(monkeypatch, [], "ezviz", ezviz_source_id=SOURCE)
    test.client.ezviz_camera_identity.return_value = "OTHER:1"
    await poll(test)
    assert created(test) == [
        ("ezviz_binding_unavailable_entry-1", "ezviz_binding_mismatch", "error")
    ]


async def test_unanswered_identity_check_waits_and_never_claims_a_change(monkeypatch) -> None:
    test = env(monkeypatch, [0, 899, 900], "ezviz", ezviz_source_id=SOURCE)
    test.client.ezviz_camera_identity.side_effect = CannotConnectError
    await poll(test)
    await poll(test)
    assert created(test) == []
    await poll(test)
    assert created(test) == [
        ("ezviz_binding_unavailable_entry-1", "ezviz_binding_unavailable", "warning")
    ]
    test.client.ezviz_camera_identity.side_effect = None
    assert await test.coordinator._async_update_data() == "1.0"
    assert deleted(test)[-1] == "ezviz_binding_unavailable_entry-1"


async def test_revoked_ezviz_session_starts_reauth_without_a_repair(monkeypatch) -> None:
    test = env(monkeypatch, [], "ezviz", ezviz_source_id=SOURCE)
    test.client.ezviz_camera_identity.side_effect = ReauthRequiredError
    await poll(test, AuthFailedError)
    assert created(test) == []


def test_entry_issues_are_removed_and_clocks_forgotten(monkeypatch) -> None:
    issues = stub_ha(monkeypatch)
    repairs = load(monkeypatch, "repairs")
    outage.outage_clock("bridge_unavailable_entry-1").since = 5
    outage.outage_clock("bridge_unavailable_entry-2").since = 5
    repairs.remove_entry_issues(SimpleNamespace(), "entry-1")
    assert [call.args[2] for call in issues.async_delete_issue.call_args_list] == [
        "bridge_unavailable_entry-1",
        "ring_push_unavailable_entry-1",
        "ring_push_silent_entry-1",
        "ezviz_binding_unavailable_entry-1",
    ]
    # Unload (and reload) keeps the outage start; removal forgets it.
    assert outage.outage_clock("bridge_unavailable_entry-1").since == 5
    repairs.remove_entry_issues(SimpleNamespace(), "entry-1", forget=True)
    assert outage.outage_clock("bridge_unavailable_entry-1").since is None
    assert outage.outage_clock("bridge_unavailable_entry-2").since == 5


async def test_ezviz_media_poll_maps_a_revoked_session_to_reauth(monkeypatch) -> None:
    stub_ha(monkeypatch)
    media = load(monkeypatch, "ezviz_media")
    client = SimpleNamespace(ezviz_encryption=AsyncMock(side_effect=ReauthRequiredError))
    bridge = SimpleNamespace(last_update_success=True)
    entry = config_entry("ezviz")
    coordinator = media.EzvizMediaCoordinator(SimpleNamespace(), entry, client, bridge)
    with pytest.raises(AuthFailedError):
        await coordinator._async_update_data()
    client.ezviz_encryption.side_effect = CannotConnectError
    with pytest.raises(UpdateFailedError):
        await coordinator._async_update_data()


def test_native_ezviz_retry_that_recovers_within_the_grace_stays_silent(monkeypatch) -> None:
    issues = stub_ha(monkeypatch)
    load(monkeypatch, "repairs")
    core = load(monkeypatch, "ezviz_core")
    monkeypatch.setattr(outage, "time", SimpleNamespace(monotonic=lambda: 0))
    vistoda = config_entry("ezviz", ezviz_source_id=SOURCE)
    vistoda.options = {"ezviz_delegate_controls": True}
    native = SimpleNamespace(state=SimpleNamespace(value="setup_retry"), data={})
    entries = {"ezviz": [native], "media_bridge": [vistoda]}
    hass = SimpleNamespace(
        is_running=True, config_entries=SimpleNamespace(async_entries=entries.__getitem__)
    )
    core.refresh_core_issue(hass)
    native.state = SimpleNamespace(value="loaded")
    core.refresh_core_issue(hass)
    issues.async_create_issue.assert_not_called()
    assert issues.async_delete_issue.call_args.args[2] == "ezviz_core_unavailable"
    assert outage.outage_clock("ezviz_core_unavailable").since is None
