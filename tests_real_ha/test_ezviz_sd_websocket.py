"""Saving a microSD interval through the real Home Assistant websocket layer."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from custom_components.media_bridge import provider_recording_websocket as recordings
from custom_components.media_bridge.errors import RateLimitedError

REQUEST = "00000000-0000-4000-8000-0000000000aa"


def connection(admin=True):
    return SimpleNamespace(
        user=SimpleNamespace(is_admin=admin),
        send_result=Mock(),
        send_error=Mock(),
        async_handle_exception=Mock(),
    )


def message(start=1000, end=1030):
    return {"id": 7, "entry_id": "fixture", "start": start, "end": end, "request_id": REQUEST}


async def run(hass, conn, msg, client):
    runtime = SimpleNamespace(client=client)
    with (
        patch.object(recordings, "_resolve", return_value=(runtime, "front")),
        patch.object(recordings, "async_verify_native", AsyncMock()),
    ):
        recordings.ws_create_sd_recording(hass, conn, msg)
        await hass.async_block_till_done(wait_background_tasks=True)


async def test_an_admin_saves_the_interval_through_the_bridge(hass):
    conn = connection()
    created = AsyncMock(return_value={"status": "pending"})
    await run(hass, conn, message(), SimpleNamespace(create_provider_sd_recording=created))
    created.assert_awaited_once_with("front", (1000, 1030), REQUEST)
    conn.send_result.assert_called_once_with(7, {"status": "pending"})


async def test_live_view_and_bounds_are_reported_not_forwarded(hass):
    refused = AsyncMock(side_effect=RateLimitedError)
    conn = connection()
    await run(hass, conn, message(), SimpleNamespace(create_provider_sd_recording=refused))
    conn.send_error.assert_called_once_with(7, "live_active", "Stop live view to save the clip")
    created = AsyncMock()
    for start, end in ((10, 10), (10, 9), (10, 611)):
        conn = connection()
        await run(
            hass, conn, message(start, end), SimpleNamespace(create_provider_sd_recording=created)
        )
        assert conn.send_error.call_args.args[1] == "invalid_format"
    created.assert_not_awaited()


async def test_non_admins_cannot_save_clips(hass):
    conn = connection(admin=False)
    created = AsyncMock()
    await run(hass, conn, message(), SimpleNamespace(create_provider_sd_recording=created))
    assert conn.send_error.call_args.args[1] == "unauthorized"
    created.assert_not_awaited()
