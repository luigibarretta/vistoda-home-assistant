"""Run automatic archive copies offline without camera or network mutations."""

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from release_flow_support import entry, framework


def setup_worker(monkeypatch):
    env = framework(monkeypatch)
    module = env.load("blink_usb_auto_backup")
    configured = entry("blink")
    configured.options["blink_usb_auto_backup"] = True
    env.hass.data = {
        "blink_live_bridge": {
            "runtime": SimpleNamespace(client=SimpleNamespace(get_json=AsyncMock()))
        }
    }
    monkeypatch.setattr(module, "storage_readiness", lambda mount: {"ready": True})
    return env, module, module.UsbAutoBackup(env.hass, configured)


def batch(ids, more=False):
    return {
        "storages": [
            {
                "network_id": 1,
                "sync_module_id": 2,
                "manifest_id": 3,
                "pagination": {"has_next": more},
                "clips": [
                    {"id": key, "device_name": "Front Door", "media_available": True} for key in ids
                ],
            }
        ]
    }


async def test_absent_mount_never_contacts_blink(monkeypatch):
    env, module, worker = setup_worker(monkeypatch)
    monkeypatch.setattr(
        module,
        "storage_readiness",
        lambda mount: {"ready": False, "reason": "network_mount_missing"},
    )
    assert (await worker.run())["status"] == "network_mount_missing"
    env.hass.data["blink_live_bridge"]["runtime"].client.get_json.assert_not_called()


async def test_disabled_tick_and_overlapping_tick_do_not_start_work(monkeypatch):
    _env, _module, worker = setup_worker(monkeypatch)
    worker.run = AsyncMock()
    worker.entry.options["blink_usb_auto_backup"] = False
    await worker.tick(None)
    worker.entry.options["blink_usb_auto_backup"] = True
    worker.running = True
    await worker.tick(None)
    worker.run.assert_not_called()


async def test_existing_clips_do_not_consume_new_file_budget_and_pages_continue(monkeypatch):
    env, module, worker = setup_worker(monkeypatch)
    client = env.hass.data["blink_live_bridge"]["runtime"].client
    client.get_json.side_effect = [batch(range(1, 31), True), batch([31])]
    copy = AsyncMock(side_effect=[{"status": "existing"}] * 30 + [{"status": "created"}])
    monkeypatch.setattr(module, "_backup_clip", copy)
    assert await worker.run() == {"status": "complete", "created": 1, "checked": 31}
    assert client.get_json.call_count == 2
    assert copy.call_args.args[1]["camera"] == "Front_Door"


async def test_new_file_budget_stops_before_next_download(monkeypatch):
    env, module, worker = setup_worker(monkeypatch)
    env.hass.data["blink_live_bridge"]["runtime"].client.get_json.return_value = batch(
        range(1, 51), True
    )
    copy = AsyncMock(return_value={"status": "created"})
    monkeypatch.setattr(module, "_backup_clip", copy)
    assert await worker.run() == {"status": "pending", "created": 20, "checked": 20}
    assert copy.call_count == 20


async def test_unload_cancels_inflight_worker(monkeypatch):
    _env, _module, worker = setup_worker(monkeypatch)
    waiting = asyncio.Event()
    worker.run = waiting.wait
    task = asyncio.create_task(worker.tick(None))
    await asyncio.sleep(0)
    worker.cancel()
    result = await asyncio.gather(task, return_exceptions=True)
    assert isinstance(result[0], asyncio.CancelledError)
    assert not worker.running and worker.task is None


async def test_usb_existing_backup_verifies_locally_without_contacting_provider(
    monkeypatch, tmp_path
):
    env = framework(monkeypatch)
    backup = env.load("blink_usb_backup")
    target = tmp_path / "3-1.mp4"
    target.write_bytes(b"test clip")
    message = {
        "network_id": 1,
        "sync_module_id": 2,
        "manifest_id": 3,
        "clip_id": 1,
        "camera": "Front",
        "created_at": "",
    }
    configured = entry("blink")
    monkeypatch.setattr(backup, "provider_entry", lambda *args: configured)
    monkeypatch.setattr(backup, "configured_mount", lambda entry: tmp_path)
    monkeypatch.setattr(backup, "_prepare", lambda *args: (target, True))
    client = SimpleNamespace(stream=AsyncMock())
    env.hass.data = {"blink_live_bridge": {"runtime": SimpleNamespace(client=client)}}
    assert (await backup._backup_clip(env.hass, message))["status"] == "existing"
    client.stream.assert_not_called()
    sidecar = target.with_suffix(".mp4.json")
    original_metadata = sidecar.read_bytes()
    target.write_bytes(b"tampered!")
    with pytest.raises(OSError, match="checksum mismatch"):
        await backup._backup_clip(env.hass, message)
    assert sidecar.read_bytes() == original_metadata
    assert json.loads(original_metadata)["source"]["clip_id"] == 1
