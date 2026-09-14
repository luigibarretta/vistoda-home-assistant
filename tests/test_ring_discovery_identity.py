"""Supervisor aliases must not rediscover or retarget a configured intercom."""

from copy import deepcopy
from types import SimpleNamespace

import pytest
from release_flow_support import entry, framework

from custom_components.media_bridge.errors import CannotConnectError


def discovery(configured, **overrides):
    return SimpleNamespace(
        config={
            **configured.data,
            "devices": [{"alias": "intercom-123", "device_id": "123"}],
            **overrides,
        }
    )


async def test_generated_alias_adopts_same_device_preserving_every_identity(monkeypatch):
    env = framework(monkeypatch)
    configured = entry(ring_device_id="123", ring_official_binding={"device_id": "official"})
    before = deepcopy(vars(configured))
    flow = env.make_flow(configured)
    client = flow._validated_client.return_value
    client.ring_status.return_value = SimpleNamespace(device_id="123")
    for _ in range(2):
        result = await flow.async_step_hassio(discovery(configured))
        assert result == {"type": "abort", "reason": "managed_app_adopted"}
        assert vars(configured) == before
    client.ring_status.assert_awaited_with("entrance")
    client.start_ring_enrollment.assert_not_called()
    env.hass.config_entries.async_reload.assert_not_called()
    env.hass.config_entries.flow.async_init.assert_not_called()


async def test_generated_alias_can_refresh_bridge_token_without_renaming(monkeypatch):
    env = framework(monkeypatch)
    configured = entry(ring_device_id="123")
    flow = env.make_flow(configured)
    flow._validated_client.return_value.ring_status.return_value = SimpleNamespace(device_id="123")
    result = await flow.async_step_hassio(discovery(configured, api_token="y" * 32))
    assert result["reason"] == "managed_app_adopted"
    assert configured.data["alias"] == "entrance"
    assert configured.data["api_token"] == "y" * 32
    assert configured.unique_id == "old-unique-id"
    env.hass.config_entries.async_reload.assert_awaited_once_with(configured.entry_id)


@pytest.mark.parametrize("actual", ["999", None])
async def test_changed_or_missing_live_identity_cannot_adopt(monkeypatch, actual):
    env = framework(monkeypatch)
    configured = entry(ring_device_id="123")
    before = deepcopy(vars(configured))
    flow = env.make_flow(configured)
    flow._validated_client.return_value.ring_status.return_value = SimpleNamespace(device_id=actual)
    result = await flow.async_step_hassio(discovery(configured))
    assert result["reason"] == "discovered_device_changed"
    assert vars(configured) == before
    env.hass.config_entries.async_reload.assert_not_called()


async def test_unreachable_existing_alias_does_not_rebind_or_reenroll(monkeypatch):
    env = framework(monkeypatch)
    configured = entry(ring_device_id="123")
    flow = env.make_flow(configured)
    client = flow._validated_client.return_value
    client.ring_status.side_effect = CannotConnectError
    result = await flow.async_step_hassio(discovery(configured))
    assert result["reason"] == "cannot_connect"
    assert configured.data["alias"] == "entrance"
    client.start_ring_enrollment.assert_not_called()
    env.hass.config_entries.async_reload.assert_not_called()


@pytest.mark.parametrize("other_id", ["123", "999"])
async def test_alias_and_physical_identity_ambiguity_fails_closed(monkeypatch, other_id):
    env = framework(monkeypatch)
    configured = entry(ring_device_id="123")
    flow = env.make_flow(configured)
    other = entry(key="entry-b", alias="intercom-123", ring_device_id=other_id)
    env.entries[other.entry_id] = other
    before = deepcopy([vars(configured), vars(other)])
    result = await flow.async_step_hassio(discovery(configured))
    assert result["reason"] == "discovered_device_changed"
    assert [vars(configured), vars(other)] == before
    env.hass.config_entries.async_reload.assert_not_called()


@pytest.mark.parametrize(
    "device_id,url",
    [
        (None, "http://bridge.local:8787"),
        ("999", "http://bridge.local:8787"),
        ("123", "http://other.local:8787"),
    ],
)
async def test_unrelated_or_unbound_device_is_not_adopted(monkeypatch, device_id, url):
    env = framework(monkeypatch)
    configured = entry(ring_device_id=device_id)
    flow = env.make_flow(configured)
    result = await flow.async_step_hassio(discovery(configured, url=url))
    assert result["step_id"] == "ring_credentials"
    assert configured.data["alias"] == "entrance"
    flow._validated_client.return_value.ring_status.assert_not_called()


async def test_existing_intercom_does_not_hide_a_second_new_intercom(monkeypatch):
    env = framework(monkeypatch)
    configured = entry(ring_device_id="123")
    flow = env.make_flow(configured)
    flow._validated_client.return_value.ring_status.return_value = SimpleNamespace(device_id="123")
    result = await flow.async_step_hassio(
        discovery(
            configured,
            devices=[
                {"alias": "intercom-123", "device_id": "123"},
                {"alias": "south", "device_id": "222"},
            ],
        )
    )
    assert result["type"] == "create_entry"
    assert result["data"]["alias"] == "south"
    assert result["data"]["ring_device_id"] == "222"
    assert configured.data["alias"] == "entrance"
