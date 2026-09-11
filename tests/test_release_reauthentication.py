"""Account recovery and aggregate discovery preserve exact existing identities."""

from types import SimpleNamespace

import pytest
from release_flow_support import entry, framework

from custom_components.media_bridge.errors import InvalidOtpError


@pytest.mark.parametrize("provider", ["ring", "ezviz"])
async def test_reauth_keeps_entry_identity_options_and_vendor_password_ephemeral(
    monkeypatch, provider
):
    env = framework(monkeypatch)
    configured = entry(provider, ring_device_id="123", ring_official_binding={"device_id": "known"})
    original = dict(configured.data)
    flow = env.make_flow(configured)
    assert (await flow.async_step_reauth(original))["step_id"] == "reauth_confirm"
    assert (await flow.async_step_reauth_confirm({}))["step_id"] == f"{provider}_credentials"
    client = flow._client
    getattr(client, f"start_{provider}_enrollment").return_value = SimpleNamespace(
        next_step="complete", enrollment_id="one-use"
    )
    data = {
        "email": "private@example",
        "account": "private@example",
        "password": "vendor-secret",
        "api_region": "eu",
    }
    result = await getattr(flow, f"async_step_{provider}_credentials")(data)
    assert result == {"type": "abort", "reason": "reauth_successful"}
    target, updates = flow.updated
    assert target is configured and updates["data_updates"] == {}
    assert configured.data == original and configured.unique_id == "old-unique-id"
    assert (
        configured.title == "My entrance"
        and configured.options["backup_storage"] == "family_archive"
    )
    assert "vendor-secret" not in repr(flow._bridge_data) and flow._enrollment_id is None


async def test_wrong_otp_restarts_reauth_without_creating_or_replacing_entry(monkeypatch):
    env = framework(monkeypatch)
    configured = entry()
    flow = env.make_flow(configured)
    await flow.async_step_reauth(configured.data)
    await flow.async_step_reauth_confirm({})
    flow._client.start_ring_enrollment.return_value = SimpleNamespace(
        next_step="otp", enrollment_id="old"
    )
    assert (await flow.async_step_ring_credentials({"email": "a", "password": "secret"}))[
        "step_id"
    ] == "otp"
    flow._client.verify_enrollment.side_effect = InvalidOtpError
    result = await flow.async_step_otp({"code": "000000"})
    assert result["step_id"] == "ring_credentials"
    assert result["errors"]["base"] == "invalid_otp_restart"
    assert flow._reauth_entry is configured and flow._enrollment_id is None
    assert not hasattr(flow, "updated")


async def test_aggregate_discovery_selects_device_and_continues_without_relogin(monkeypatch):
    env = framework(monkeypatch)
    flow = env.make_flow()
    config = {
        **entry().data,
        "devices": [{"alias": "north", "device_id": "111"}, {"alias": "south", "device_id": "222"}],
    }
    result = await flow.async_step_hassio(SimpleNamespace(config=config))
    assert result["step_id"] == "managed_device"
    assert (await flow.async_step_managed_device({"alias": "south"}))[
        "step_id"
    ] == "ring_credentials"
    flow._client.start_ring_enrollment.return_value = SimpleNamespace(next_step="complete")
    result = await flow.async_step_ring_credentials({"email": "a", "password": "secret"})
    assert result["data"]["alias"] == "south" and result["data"]["ring_device_id"] == "222"
    continuation = env.hass.config_entries.flow.async_init.call_args.kwargs["data"]
    assert "secret" not in repr(continuation)
    next_flow = env.make_flow()
    result = await next_flow.async_step_integration_discovery(continuation)
    assert result["type"] == "create_entry" and result["data"]["alias"] == "north"
    next_flow._client.start_ring_enrollment.assert_not_called()


async def test_discovery_preserves_existing_entries_and_refuses_physical_retarget(monkeypatch):
    env = framework(monkeypatch)
    existing = entry(ring_device_id="123", ring_official_binding={"device_id": "official"})
    flow = env.make_flow(existing)
    config = {**existing.data, "devices": [{"alias": "entrance", "device_id": "999"}]}
    assert (await flow.async_step_hassio(SimpleNamespace(config=config)))[
        "reason"
    ] == "discovered_device_changed"
    assert existing.data["ring_device_id"] == "123"
    config["devices"][0]["device_id"] = "123"
    config["api_token"] = "y" * 32
    assert (await flow.async_step_hassio(SimpleNamespace(config=config)))[
        "reason"
    ] == "managed_app_adopted"
    assert existing.data["api_token"] == "y" * 32
    assert existing.data["ring_official_binding"] == {"device_id": "official"}
    assert existing.unique_id == "old-unique-id"


async def test_same_alias_on_different_endpoints_is_not_adopted(monkeypatch):
    env = framework(monkeypatch)
    existing = entry()
    flow = env.make_flow(existing)
    config = {**existing.data, "url": "http://second.local:8787"}
    result = await flow.async_step_hassio(SimpleNamespace(config=config))
    assert result["step_id"] == "ring_credentials"
    assert existing.data["url"] == "http://bridge.local:8787"


async def test_unbound_bootstrap_discovers_real_intercoms_and_creates_exact_selection(monkeypatch):
    env = framework(monkeypatch)
    flow = env.make_flow()
    assert (await flow.async_step_hassio(SimpleNamespace(config=entry().data)))[
        "step_id"
    ] == "ring_credentials"
    flow._client.start_ring_enrollment.return_value = SimpleNamespace(next_step="complete")
    result = await flow.async_step_ring_credentials({"email": "a", "password": "secret"})
    assert result["step_id"] == "ring_device"
    flow._client.ring_intercoms.assert_awaited_once()
    result = await flow.async_step_ring_device({"device_id": "222"})
    assert result["type"] == "create_entry"
    assert result["data"]["alias"] == "south" and result["data"]["ring_device_id"] == "222"
    assert "password" not in result["data"]
    continuation = env.hass.config_entries.flow.async_init.call_args.kwargs["data"][
        "managed_continuation"
    ]
    assert continuation["devices"] == [{"alias": "north", "device_id": "111"}]


async def test_legacy_inventory_never_guesses_an_alias_for_multiple_intercoms(monkeypatch):
    env = framework(monkeypatch)
    flow = env.make_flow()
    await flow.async_step_hassio(SimpleNamespace(config=entry().data))
    flow._client.ring_intercoms.return_value = [
        {"alias": None, "device_id": "111", "name": "One", "location_name": None},
        {"alias": None, "device_id": "222", "name": "Two", "location_name": None},
    ]
    result = await flow.async_step_ring_device()
    assert result["errors"]["base"] == "no_routable_intercoms"
    flow._client.ring_status.assert_not_called()


async def test_single_legacy_alias_requires_exact_physical_status_match(monkeypatch):
    env = framework(monkeypatch)
    flow = env.make_flow()
    await flow.async_step_hassio(SimpleNamespace(config=entry().data))
    flow._client.ring_intercoms.return_value = [
        {"alias": None, "device_id": "111", "name": "One", "location_name": None}
    ]
    flow._client.ring_status.return_value = SimpleNamespace(device_id="999")
    result = await flow.async_step_ring_device()
    assert result["errors"]["base"] == "no_routable_intercoms"
    flow._client.ring_status.return_value = SimpleNamespace(device_id="111")
    result = await flow.async_step_ring_device()
    assert result["step_id"] == "ring_device" and result["errors"] == {}
