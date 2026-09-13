"""Camera-only accounts must never set up Intercom entities or status polling."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import current_entry

from custom_components import media_bridge
from custom_components.media_bridge.config_flow import ConfigFlow
from custom_components.media_bridge.const import DOMAIN

from .conftest import register_entry
from .test_runtime import make_entry


async def test_camera_only_account_setup_does_not_bind_an_intercom(hass):
    entry = make_entry()
    await register_entry(hass, entry)
    hass.config_entries.async_update_entry(
        entry,
        data={
            **entry.data,
            "provider": "ring",
            "alias": "camera-account",
            "ring_camera_account": True,
        },
    )
    with (
        patch.object(
            media_bridge.BridgeClient,
            "health",
            AsyncMock(return_value=SimpleNamespace(version="fixture")),
        ),
        patch.object(media_bridge.BridgeClient, "ring_status", AsyncMock()) as status,
        patch.object(hass.config_entries, "async_forward_entry_setups", AsyncMock()) as forward,
        current_entry.set(entry),
    ):
        assert await media_bridge.async_setup_entry(hass, entry)
    status.assert_not_awaited()
    forward.assert_not_awaited()
    assert hass.data[DOMAIN][entry.entry_id].ring_status is None
    assert await media_bridge.async_unload_entry(hass, entry)
    assert entry.entry_id not in hass.data[DOMAIN]


async def test_empty_intercom_inventory_can_enroll_camera_account(hass):
    flow = ConfigFlow()
    flow.hass = hass
    flow._bridge_data = {"provider": "ring", "alias": "legacy", "url": "http://127.0.0.1:9"}
    client = SimpleNamespace(ring_intercoms=AsyncMock(return_value=[]))
    with (
        patch.object(flow, "_require_client", return_value=client),
        patch.object(flow, "_finish", AsyncMock(return_value={"finished": True})),
        patch(
            "custom_components.media_bridge.client_ring_camera.cameras",
            AsyncMock(return_value=[{"device_id": "123"}]),
        ),
    ):
        assert await flow.async_step_ring_device() == {"finished": True}
    assert flow._bridge_data["ring_camera_account"] is True
    assert flow._bridge_data["alias"] == "camera-account"
    assert "ring_device_id" not in flow._bridge_data
