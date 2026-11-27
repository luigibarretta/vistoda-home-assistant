"""Blink recordings are copied as MP4, with the original's checksum kept in the metadata."""

import hashlib
import io
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from release_flow_support import framework
from test_ts_remux import synthetic_ts

from custom_components.media_bridge import backup_storage as storage

av = pytest.importorskip("av")

ID = "00000000-0000-4000-8000-000000000001"


def setup(monkeypatch, tmp_path):
    env = framework(monkeypatch)
    backup = env.load("recording_backup")
    archive = env.load("network_archive")
    mount = tmp_path / "mounted"
    mount.mkdir()
    monkeypatch.setattr(storage, "network_filesystem", lambda path, writable=True: "nfs4")
    monkeypatch.setattr(archive, "network_filesystem", lambda path, writable=True: "nfs4")
    monkeypatch.setattr(backup.shutil, "disk_usage", lambda path: SimpleNamespace(free=10**10))
    return env, backup, archive, mount


def manifest_for(payload: bytes, media_type="video/mp2t"):
    return {
        "recording_id": ID,
        "camera": "front",
        "status": "ready",
        "media_type": media_type,
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "requested_at": "2026-11-27T10:00:00Z",
    }


def upstream_for(payload: bytes):
    class Content:
        async def iter_chunked(self, size):
            yield payload

    return SimpleNamespace(status=200, content_type="video/mp2t", content=Content(), release=Mock())


async def test_new_copy_is_an_mp4_that_keeps_the_originals_checksum(monkeypatch, tmp_path):
    env, backup, archive, mount = setup(monkeypatch, tmp_path)
    payload = synthetic_ts(tmp_path).read_bytes()
    manifest = manifest_for(payload)
    result = await backup._backup(env.hass, "blink", manifest, upstream_for(payload), mount)
    target = mount / result["relative_path"]
    assert result["status"] == "created" and target.name == f"{ID}.mp4"
    with av.open(io.BytesIO(target.read_bytes())) as video:
        assert video.streams.video[0].codec_context.name == "h264"
    sidecar = json.loads((mount / "blink" / "front" / f"{ID}.mp4.json").read_text())
    assert sidecar["recording"]["sha256"] == manifest["sha256"]
    assert sidecar["stored"]["sha256"] == hashlib.sha256(target.read_bytes()).hexdigest()
    assert sidecar["stored"]["bytes"] == target.stat().st_size
    # Already copied: recognised by the original's checksum, nothing rewritten.
    before = target.stat().st_mtime_ns
    again = await backup._backup(env.hass, "blink", manifest, upstream_for(payload), mount)
    assert again["status"] == "existing" and target.stat().st_mtime_ns == before
    # The archive lists it as MP4 and verifies the MP4's own checksum.
    _, item = archive.checked_file(mount, result["relative_path"], checksum=True)
    assert item["media_type"] == "video/mp4" and item["media_id"] == f"local:{ID}"
    target.write_bytes(target.read_bytes()[:-1] + b"\x00")
    with pytest.raises(ValueError, match=r"size|checksum"):
        archive.checked_file(mount, result["relative_path"], checksum=True)


async def test_a_ts_copy_made_earlier_counts_as_already_backed_up(monkeypatch, tmp_path):
    _env, backup, _archive, mount = setup(monkeypatch, tmp_path)
    payload = synthetic_ts(tmp_path).read_bytes()
    folder = mount / "blink" / "front"
    folder.mkdir(parents=True)
    (folder / f"{ID}.ts").write_bytes(payload)
    target, existing = backup._prepare("blink", manifest_for(payload), mount)
    assert existing and target.name == f"{ID}.ts"


async def test_a_copy_of_another_recording_is_never_overwritten_but_a_torn_one_is(
    monkeypatch, tmp_path
):
    env, backup, _archive, mount = setup(monkeypatch, tmp_path)
    payload = synthetic_ts(tmp_path).read_bytes()
    manifest = manifest_for(payload)
    folder = mount / "blink" / "front"
    folder.mkdir(parents=True)
    (folder / f"{ID}.mp4").write_bytes(b"torn copy")  # No metadata: an interrupted copy.
    result = await backup._backup(env.hass, "blink", manifest, upstream_for(payload), mount)
    assert result["status"] == "created"
    with pytest.raises(OSError, match="different recording"):
        backup._prepare("blink", {**manifest, "sha256": "0" * 64}, mount)


async def test_unconvertible_video_is_kept_as_the_original_ts(monkeypatch, tmp_path):
    env, backup, _archive, mount = setup(monkeypatch, tmp_path)
    payload = b"G" + b"not really a transport stream" * 10
    manifest = manifest_for(payload)
    result = await backup._backup(env.hass, "blink", manifest, upstream_for(payload), mount)
    target = mount / result["relative_path"]
    assert target.name == f"{ID}.ts" and target.read_bytes() == payload
    assert not (mount / "blink" / "front" / f"{ID}.mp4").exists()
