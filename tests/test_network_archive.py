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
    monkeypatch.setattr(module, "network_filesystem", lambda path, **_: "nfs")
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
    monkeypatch.setattr(module, "network_filesystem", lambda path, **_: None)
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


def test_ezviz_copies_are_listed_with_their_media_type(monkeypatch, tmp_path):
    module = fixture(monkeypatch, tmp_path)
    folder = tmp_path / "ezviz" / "front-door"
    folder.mkdir(parents=True)
    for number, (extension, media_type) in enumerate(
        (("mpegps", "video/mpeg"), ("ts", "video/mp2t")), start=1
    ):
        recording_id = f"00000000-0000-4000-8000-00000000000{number}"
        (folder / f"{recording_id}.{extension}").write_bytes(b"clip")
        metadata = {
            "schema_version": 1,
            "provider": "ezviz",
            "recording": {
                "recording_id": recording_id,
                "camera": "front-door",
                "requested_at": f"2026-10-2{number}T10:00:00Z",
                "media_type": media_type,
                "bytes": 4,
                "sha256": hashlib.sha256(b"clip").hexdigest(),
            },
        }
        (folder / f"{recording_id}.{extension}.json").write_text(json.dumps(metadata))
    items = module.inventory(tmp_path, 1, 50, "front-door")["items"]
    assert [(item["id"].split("/")[0], item["media_type"]) for item in items] == [
        ("ezviz", "video/mp2t"),
        ("ezviz", "video/mpeg"),
    ]
    module.checked_file(tmp_path, items[1]["id"], checksum=True)
    (folder / "00000000-0000-4000-8000-000000000001.mpegps.json").write_text(
        json.dumps({**metadata, "provider": "blink"})
    )
    assert len(module.inventory(tmp_path, 1, 50, "front-door")["items"]) == 1


def test_recording_copies_carry_their_time_span(monkeypatch, tmp_path):
    module = fixture(monkeypatch, tmp_path)
    folder = tmp_path / "ezviz" / "front-door"
    folder.mkdir(parents=True)
    copies = {
        "00000000-0000-4000-8000-0000000000a1": {"source": "sd", "sd_start": 100, "sd_end": 160},
        "00000000-0000-4000-8000-0000000000a2": {
            "started_at": "2026-10-28T19:00:00Z",
            "actual_duration_seconds": 30.4,
        },
        "00000000-0000-4000-8000-0000000000a3": {},
    }
    for recording_id, extra in copies.items():
        (folder / f"{recording_id}.mpegps").write_bytes(b"clip")
        recording = {
            "recording_id": recording_id,
            "camera": "front-door",
            "requested_at": "2026-10-28T19:00:00Z",
            "media_type": "video/mpeg",
            "bytes": 4,
            "sha256": hashlib.sha256(b"clip").hexdigest(),
            **extra,
        }
        metadata = {"schema_version": 1, "provider": "ezviz", "recording": recording}
        (folder / f"{recording_id}.mpegps.json").write_text(json.dumps(metadata))
    items = module.inventory(tmp_path, 1, 50, "front-door")["items"]
    spans = {item["id"].rsplit("/", 1)[1][:36]: item["span"] for item in items}
    assert spans["00000000-0000-4000-8000-0000000000a1"] == [100, 160]
    assert spans["00000000-0000-4000-8000-0000000000a2"] == [1793214000, 1793214030]
    assert spans["00000000-0000-4000-8000-0000000000a3"] is None


def test_archive_entries_are_blink_or_ezviz(monkeypatch):
    module = framework(monkeypatch).load("backup_storage")
    entries = {key: SimpleNamespace(data={"provider": key}) for key in ("blink", "ezviz", "ring")}
    hass = SimpleNamespace(config_entries=SimpleNamespace(async_get_entry=entries.get))
    assert module.archive_entry(hass, "ezviz") is entries["ezviz"]
    assert module.archive_entry(hass, "blink") is entries["blink"]
    for refused in ("ring", "missing"):
        with pytest.raises(ValueError):
            module.archive_entry(hass, refused)
