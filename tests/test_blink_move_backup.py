"""Move-after-copy, the USB opt-out and the pass interval of the Blink auto-backup."""

from unittest.mock import AsyncMock

import pytest
from test_blink_auto_backup import IDS, manifest, worker_fixture, ws_fixture


def moving_fixture(monkeypatch, tmp_path, count=3):
    items = [manifest(IDS[n % 3], b"x") | {"recording_id": IDS[n]} for n in range(count)]
    live = list(items)

    def pages(path):
        if path.startswith("/v1/local-storage"):
            return {"storages": []}
        return {"recordings": list(live), "pagination": {"has_next": False}}

    env, local, worker, client = worker_fixture(monkeypatch, tmp_path, pages)

    async def delete(path):
        recording_id = path.rsplit("/", 1)[1]
        live[:] = [item for item in live if item["recording_id"] != recording_id]

    client.delete = AsyncMock(side_effect=delete)
    return env, local, worker, client, live


async def test_move_deletes_each_recording_only_after_its_verified_copy(monkeypatch, tmp_path):
    _env, local, worker, client, live = moving_fixture(monkeypatch, tmp_path)
    copy = AsyncMock(
        side_effect=[{"status": "created"}, {"status": "existing"}, {"status": "created"}]
    )
    monkeypatch.setattr(local, "backup_local_recording", copy)
    worker.entry.options["blink_move_after_backup"] = True
    result = await worker.run()
    assert result["status"] == "complete" and result["local_created"] == 2
    assert [call.args[0] for call in client.delete.await_args_list] == [
        f"/v1/recordings/{IDS[n]}" for n in range(3)
    ]
    assert live == [] and worker.local_page == 1


async def test_without_move_nothing_is_deleted(monkeypatch, tmp_path):
    _env, local, worker, client, live = moving_fixture(monkeypatch, tmp_path)
    monkeypatch.setattr(
        local, "backup_local_recording", AsyncMock(return_value={"status": "created"})
    )
    await worker.run()
    client.delete.assert_not_awaited()
    assert len(live) == 3


async def test_a_failed_copy_is_never_followed_by_a_delete(monkeypatch, tmp_path):
    _env, local, worker, client, live = moving_fixture(monkeypatch, tmp_path)
    copy = AsyncMock(side_effect=[{"status": "created"}, OSError("checksum mismatch")])
    monkeypatch.setattr(local, "backup_local_recording", copy)
    worker.entry.options["blink_move_after_backup"] = True
    with pytest.raises(OSError):
        await worker.run()
    assert client.delete.await_count == 1
    assert [item["recording_id"] for item in live] == IDS[1:]


async def test_usb_is_skipped_when_the_user_turns_it_off(monkeypatch, tmp_path):
    _env, local, worker, _client, _live = moving_fixture(monkeypatch, tmp_path)
    worker.usb_pass = AsyncMock(side_effect=AssertionError("USB must not be read"))
    monkeypatch.setattr(
        local, "backup_local_recording", AsyncMock(return_value={"status": "created"})
    )
    worker.entry.options["blink_use_usb"] = False
    result = await worker.run()
    assert result["status"] == "complete" and result["local_created"] == 3
    worker.usb_pass.assert_not_awaited()


def test_the_pass_interval_follows_the_option(monkeypatch, tmp_path):
    import time

    _env, _local, worker, _client = worker_fixture(monkeypatch, tmp_path, {})
    assert worker.due()
    worker.last_started = time.monotonic()
    assert not worker.due()
    worker.last_started = time.monotonic() - 120
    assert not worker.due()
    worker.entry.options["blink_backup_minutes"] = 1
    assert worker.due()


async def test_panel_learns_whether_usb_is_in_use(monkeypatch):
    env, module, configured, connection = ws_fixture(monkeypatch)
    message = {"id": 1, "entry_id": configured.entry_id}
    await module.ws_recording_options(env.hass, connection, message)
    assert connection.send_result.call_args.args[1] == {"use_usb": True}
    configured.options["blink_use_usb"] = False
    await module.ws_recording_options(env.hass, connection, message)
    assert connection.send_result.call_args.args[1] == {"use_usb": False}
    await module.ws_recording_options(env.hass, connection, {"id": 2, "entry_id": "missing"})
    assert connection.send_error.call_args.args[1] == "not_found"
