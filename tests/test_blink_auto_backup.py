"""Hourly HA-local copies and the panel switch, offline with mocked Blink clients."""

import hashlib
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from release_flow_support import entry, framework

from custom_components.media_bridge import backup_storage as storage

IDS = [f"00000000-0000-4000-8000-00000000000{n}" for n in range(1, 4)]


def manifest(recording_id, payload, status="ready"):
    return {
        "recording_id": recording_id,
        "camera": "front",
        "status": status,
        "media_type": "video/mp2t",
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "requested_at": "2026-10-01T10:00:00Z",
        "trigger": "motion",
    }


def worker_fixture(monkeypatch, tmp_path, pages):
    env = framework(monkeypatch)
    env.load("recording_backup")
    local = env.load("blink_local_auto_backup")
    module = env.load("blink_usb_auto_backup")
    monkeypatch.setattr(storage, "network_filesystem", lambda path, **_: "nfs4")
    monkeypatch.setattr(module, "storage_readiness", lambda mount: {"ready": True})
    monkeypatch.setattr(module, "configured_mount", lambda entry: tmp_path)

    async def get_json(path):
        return pages[path] if isinstance(pages, dict) else pages(path)

    client = SimpleNamespace(get_json=AsyncMock(side_effect=get_json), stream=AsyncMock())
    env.hass.data = {"blink_live_bridge": {"runtime": SimpleNamespace(client=client)}}
    configured = entry("blink")
    configured.options["blink_usb_auto_backup"] = True
    return env, local, module.UsbAutoBackup(env.hass, configured), client


async def test_local_recordings_follow_usb_and_existing_copies_skip_provider_media(
    monkeypatch, tmp_path
):
    old, new = b"verified copy", b"new recording"
    items = [manifest(IDS[0], old), manifest(IDS[1], new), manifest(IDS[2], b"", "recording")]
    pages = {
        "/v1/local-storage?page=1&page_size=50": {"storages": []},
        "/v1/recordings?page=1&page_size=50": {
            "recordings": items,
            "pagination": {"has_next": False},
        },
        f"/v1/recordings/{IDS[1]}": items[1],
    }
    _env, _local, worker, client = worker_fixture(monkeypatch, tmp_path, pages)
    (tmp_path / "blink" / "front").mkdir(parents=True)
    (tmp_path / "blink" / "front" / f"{IDS[0]}.ts").write_bytes(old)

    class Content:
        async def iter_chunked(self, size):
            yield new

    client.stream.return_value = SimpleNamespace(
        status=200, content_type="video/mp2t", content=Content(), release=Mock()
    )
    assert await worker.run() == {
        "status": "complete",
        "created": 1,
        "checked": 2,
        "local_created": 1,
        "local_checked": 2,
    }
    client.stream.assert_awaited_once_with(f"/v1/recordings/{IDS[1]}/media")
    assert (tmp_path / "blink" / "front" / f"{IDS[1]}.ts").read_bytes() == new
    assert (tmp_path / "blink" / "front" / f"{IDS[0]}.ts.json").is_file()
    assert worker.local_page == 1


async def test_usb_and_local_share_the_hourly_new_file_cap(monkeypatch, tmp_path):
    items = [manifest(IDS[0], b"x")] * 10

    def pages(path):
        if path.startswith("/v1/local-storage"):
            return {"storages": []}
        return {"recordings": items, "pagination": {"has_next": True}}

    _env, local, worker, _client = worker_fixture(monkeypatch, tmp_path, pages)
    worker.usb_pass = AsyncMock(return_value=("complete", 15, 40))
    copy = AsyncMock(return_value={"status": "created"})
    monkeypatch.setattr(local, "backup_local_recording", copy)
    worker.local_page = 3
    result = await worker.run()
    assert result["status"] == "pending" and result["created"] == 20
    assert result["local_created"] == 5 and copy.await_count == 5
    assert worker.local_page == 3
    worker.usb_pass.return_value = ("pending", 20, 20)
    assert (await worker.run())["local_checked"] == 0
    assert copy.await_count == 5


async def test_usb_failure_does_not_block_local_copies(monkeypatch, tmp_path):
    _env, _local, worker, _client = worker_fixture(
        monkeypatch,
        tmp_path,
        {"/v1/recordings?page=1&page_size=50": {"recordings": [], "pagination": {}}},
    )
    worker.usb_pass = AsyncMock(side_effect=ValueError("invalid USB inventory"))
    result = await worker.run()
    assert result["status"] == "unavailable" and result["local_checked"] == 0
    worker.entry.options["blink_usb_auto_backup"] = False
    worker.usb_pass = AsyncMock(return_value=("complete", 0, 0))
    assert (await worker.run())["status"] == "disabled"


def ws_fixture(monkeypatch, admin=True, provider="blink"):
    env = framework(monkeypatch)
    module = env.load("blink_auto_backup_websocket")
    configured = entry(provider)
    env.entries[configured.entry_id] = configured
    configured.runtime_data = SimpleNamespace()
    connection = SimpleNamespace(
        user=SimpleNamespace(is_admin=admin), send_error=Mock(), send_result=Mock()
    )
    return env, module, configured, connection


async def test_auto_backup_switch_requires_admin_and_a_loaded_blink_entry(monkeypatch):
    env, module, configured, connection = ws_fixture(monkeypatch, admin=False)
    readiness = Mock(side_effect=AssertionError("must not read storage"))
    monkeypatch.setattr(module, "storage_readiness", readiness)
    message = {"id": 1, "entry_id": configured.entry_id, "enabled": True}
    await module.ws_set_auto_backup(env.hass, connection, message)
    assert connection.send_error.call_args.args[1] == "unauthorized"
    assert "blink_usb_auto_backup" not in configured.options
    env, module, configured, connection = ws_fixture(monkeypatch, provider="ring")
    await module.ws_set_auto_backup(env.hass, connection, {**message, "enabled": False})
    assert connection.send_error.call_args.args[1] == "not_found"
    await module.ws_set_auto_backup(env.hass, connection, {**message, "entry_id": "missing"})
    assert connection.send_error.call_args.args[1] == "not_found"


async def test_enabling_requires_ready_storage_and_updates_options(monkeypatch):
    env, module, configured, connection = ws_fixture(monkeypatch)
    readiness = {"ready": False, "reason": "network_mount_missing"}
    monkeypatch.setattr(module, "storage_readiness", lambda mount: readiness)
    message = {"id": 1, "entry_id": configured.entry_id, "enabled": True}
    await module.ws_set_auto_backup(env.hass, connection, message)
    assert connection.send_error.call_args.args[1:] == (
        "storage_unavailable",
        "network_mount_missing",
    )
    assert "blink_usb_auto_backup" not in configured.options
    configured.options["backup_storage"] = "../outside"
    await module.ws_set_auto_backup(env.hass, connection, message)
    assert connection.send_error.call_args.args[2] == "invalid_storage_name"
    configured.options["backup_storage"] = "family_archive"
    readiness.update(ready=True, reason="ready")
    await module.ws_set_auto_backup(env.hass, connection, message)
    assert configured.options == {
        "backup_storage": "family_archive",
        "blink_usb_auto_backup": True,
    }
    assert connection.send_result.call_args.args[1]["enabled"] is True
    readiness.update(ready=False, reason="network_mount_missing")
    await module.ws_set_auto_backup(env.hass, connection, {**message, "enabled": False})
    assert configured.options["blink_usb_auto_backup"] is False


def test_switch_is_registered_with_the_other_browser_commands():
    from pathlib import Path

    source = Path("custom_components/media_bridge/websocket.py").read_text(encoding="utf-8")
    assert "register_blink_auto_backup(hass)" in source


# --- Move after backup, USB opt-out and the pass interval -------------------------------


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
    try:
        await worker.run()
    except OSError:
        pass
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
