"""No camera, NAS or production files are touched by these archive checks."""

import hashlib
import json
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock

import pytest
from release_flow_support import framework


def fixture(monkeypatch, tmp_path):
    module = framework(monkeypatch).load("network_archive")
    monkeypatch.setattr(module, "network_filesystem", lambda path: "nfs")
    root = tmp_path / "blink-usb" / "Kitchen"
    root.mkdir(parents=True)
    for number in range(1, 14):
        target = root / f"1-{number}.mp4"
        target.write_bytes(b"clip")
        metadata = {
            "schema_version": 1,
            "provider": "blink-usb",
            "bytes": 4,
            "sha256": hashlib.sha256(b"clip").hexdigest(),
            "source": {
                "network_id": 1,
                "sync_module_id": 2,
                "manifest_id": 1,
                "clip_id": number,
                "camera": "Kitchen",
                "created_at": f"2026-09-{number:02}",
            },
        }
        target.with_suffix(".mp4.json").write_text(json.dumps(metadata))
    return module


def test_server_pagination_and_source_identity(monkeypatch, tmp_path):
    module = fixture(monkeypatch, tmp_path)
    result = module.inventory(tmp_path, 2, 10)
    assert len(result["items"]) == 3
    assert result["pagination"]["total_items"] == 13
    assert result["items"][0]["media_id"] == "usb:1:2:1:3"
    assert module.inventory(tmp_path, 1, 10, "other")["items"] == []
    filtered = module.inventory(tmp_path, 1, 10, members={"usb:1:2:1:13"})
    assert filtered["pagination"]["total_items"] == 1


def test_only_complete_files_and_checksum_before_media(monkeypatch, tmp_path):
    module = fixture(monkeypatch, tmp_path)
    target = tmp_path / "blink-usb/Kitchen/1-1.mp4"
    target.write_bytes(b"fake")
    with pytest.raises(ValueError, match="checksum mismatch"):
        module.checked_file(tmp_path, "blink-usb/Kitchen/1-1.mp4", checksum=True)
    target.write_bytes(b"bad size")
    assert module.inventory(tmp_path, 1, 25)["pagination"]["total_items"] == 12


def test_reject_traversal_symlink_and_absent_mount(monkeypatch, tmp_path):
    module = fixture(monkeypatch, tmp_path)
    for path in ("../config/secrets.yaml", "/etc/passwd", "blink-usb/Kitchen/../../secret.mp4"):
        with pytest.raises(ValueError):
            module.checked_file(tmp_path, path)
    target = tmp_path / "blink-usb/Kitchen/1-1.mp4"
    # This is a file created by the isolated test above, never a user recording.
    target.unlink()
    target.symlink_to(tmp_path / "blink-usb/Kitchen/1-2.mp4")
    with pytest.raises(ValueError, match="unsafe backup path"):
        module.checked_file(tmp_path, "blink-usb/Kitchen/1-1.mp4")
    monkeypatch.setattr(module, "network_filesystem", lambda path: None)
    with pytest.raises(ValueError, match="network mount missing"):
        module.inventory(tmp_path, 1, 10)


async def test_inventory_requires_admin_before_any_filesystem_access(monkeypatch):
    env = framework(monkeypatch)
    http = ModuleType("homeassistant.components.http")
    http.HomeAssistantView = object
    monkeypatch.setitem(sys.modules, http.__name__, http)
    storage = ModuleType("homeassistant.helpers.storage")
    storage.Store = type("Store", (), {"__class_getitem__": classmethod(lambda cls, _: cls)})
    monkeypatch.setitem(sys.modules, storage.__name__, storage)
    module = env.load("network_archive_websocket")
    scan = Mock(side_effect=AssertionError("must not read storage"))
    monkeypatch.setattr(module, "inventory", scan)
    connection = SimpleNamespace(user=SimpleNamespace(is_admin=False), send_error=Mock())
    await module.ws_inventory(env.hass, connection, {"id": 1})
    assert connection.send_error.call_args.args[1] == "unauthorized"
    scan.assert_not_called()
