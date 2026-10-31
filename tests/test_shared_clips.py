"""Clips Vistoda shared with SceneTrove: listed with checks, deleted only when safe."""

import hashlib
import json
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock

from release_flow_support import framework

from custom_components.media_bridge import backup_storage as storage

ID = "0f1e2d3c-4b5a-6978-8a9b-0c1d2e3f4a5b"
NAME = f"hiv20261028T190000Z-{ID}.mpegps"
MEDIA = b"\x00\x00\x01\xba" + b"clip" * 64
RECORDING = {"recording_id": ID, "camera": "front-door", "status": "ready",
             "media_type": "video/mpeg", "source": "sd", "sd_start": 1793214000,
             "sd_end": 1793214060, "requested_at": "2026-10-28T19:05:00+00:00",
             "bytes": len(MEDIA), "sha256": hashlib.sha256(MEDIA).hexdigest()}  # fmt: skip


def shared(monkeypatch, tmp_path, *, recording=RECORDING, media=MEDIA):
    env = framework(monkeypatch)
    env.load("network_archive")
    module = env.load("shared_archive")
    monkeypatch.setattr(storage, "network_filesystem", lambda path, **_: "nfs")
    monkeypatch.setattr(module, "network_filesystem", lambda path, **_: "nfs", raising=False)
    folder = tmp_path / "spioncino"
    folder.mkdir(parents=True)
    (folder / NAME).write_bytes(media)
    sidecar = {"schema_version": 1, "provider": "ezviz", "recording": recording}
    (folder / f"{NAME}.json").write_text(json.dumps(sidecar))
    (folder / "hiv20261028T180000Z-other.mp4").write_bytes(b"scenetrove's own clip")
    return module, folder


def test_shared_clips_are_listed_with_their_identity(monkeypatch, tmp_path):
    module, _folder = shared(monkeypatch, tmp_path)
    (item,) = module.shared_inventory(tmp_path, "spioncino", "front-door")
    assert item["id"] == f"shared/{NAME}"
    assert item["media_id"] == f"local:{ID}"
    assert item["span"] == [1793214000, 1793214060]
    assert item["shared"] is True


def test_tampered_or_foreign_clips_are_not_listed(monkeypatch, tmp_path):
    module, _folder = shared(monkeypatch, tmp_path, media=MEDIA + b"x")
    assert module.shared_inventory(tmp_path, "spioncino", "front-door") == []
    module, _folder = shared(monkeypatch, tmp_path / "b", recording={**RECORDING, "camera": "x"})
    assert module.shared_inventory(tmp_path / "b", "spioncino", "front-door") == []


def test_delete_removes_the_clip_and_its_sidecar_only(monkeypatch, tmp_path):
    module, folder = shared(monkeypatch, tmp_path)
    assert module.delete_shared_clip(tmp_path, "spioncino", "front-door", f"shared/{NAME}")
    assert sorted(path.name for path in folder.iterdir()) == ["hiv20261028T180000Z-other.mp4"]
    for refused in ("shared/hiv20261028T180000Z-other.mp4", "shared/../../etc/passwd", NAME):
        assert not module.delete_shared_clip(tmp_path, "spioncino", "front-door", refused)


def ws_module(monkeypatch):
    env = framework(monkeypatch)
    http = ModuleType("homeassistant.components.http")
    http.HomeAssistantView = object
    monkeypatch.setitem(sys.modules, http.__name__, http)
    store = ModuleType("homeassistant.helpers.storage")
    store.Store = type("Store", (), {"__class_getitem__": classmethod(lambda cls, _: cls)})
    monkeypatch.setitem(sys.modules, store.__name__, store)
    return env.load("network_archive_websocket")


async def test_archive_delete_requires_admin_and_reports_failures(monkeypatch, tmp_path):
    module = ws_module(monkeypatch)
    entry = SimpleNamespace(entry_id="e", data={"provider": "ezviz", "alias": "front-door"},
                            options={"shared_storage": "scenetrove_devices"})  # fmt: skip
    hass = SimpleNamespace(config_entries=SimpleNamespace(async_get_entry={"e": entry}.get))

    async def executor(function, *args):
        return function(*args)

    hass.async_add_executor_job = executor
    monkeypatch.setattr(module, "delete_copy", lambda _mount, _shared, item: item == "keep")
    connection = SimpleNamespace(user=SimpleNamespace(is_admin=False), send_error=Mock(),
                                 send_result=Mock())  # fmt: skip
    message = {"id": 1, "entry_id": "e", "ids": ["keep", "gone"]}
    await module.ws_delete(hass, connection, message)
    assert connection.send_error.call_args.args[1] == "unauthorized"
    connection.user.is_admin = True
    await module.ws_delete(hass, connection, message)
    assert connection.send_result.call_args.args[1] == {"deleted": 1, "failed": ["gone"]}
