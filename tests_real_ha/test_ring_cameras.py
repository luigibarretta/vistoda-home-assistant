"""Camera-only accounts must never set up Intercom entities or status polling."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.config_entries import current_entry
from homeassistant.exceptions import Unauthorized

from custom_components import media_bridge
from custom_components.media_bridge import ring_camera_websocket as camera_ws
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


async def test_real_websocket_admin_guard_schedules_async_inventory(hass):
    connection = SimpleNamespace(
        user=SimpleNamespace(is_admin=True), send_result=Mock(), async_handle_exception=Mock()
    )
    with (
        patch.object(camera_ws, "resolve", return_value=object()),
        patch.object(camera_ws.camera, "cameras", AsyncMock(return_value=[])) as inventory,
    ):
        camera_ws.inventory(hass, connection, {"id": 41, "entry_id": "fixture"})
        await hass.async_block_till_done(wait_background_tasks=True)
    inventory.assert_awaited_once()
    connection.send_result.assert_called_once_with(41, {"cameras": []})
    connection.async_handle_exception.assert_not_called()


@pytest.mark.parametrize("handler", [camera_ws.inventory, camera_ws.create, camera_ws.delete])
async def test_real_websocket_rejects_non_admin_before_scheduling(hass, handler):
    connection = SimpleNamespace(user=SimpleNamespace(is_admin=False))
    with pytest.raises(Unauthorized):
        handler(hass, connection, {"id": 41})
