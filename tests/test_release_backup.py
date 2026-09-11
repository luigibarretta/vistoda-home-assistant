"""Executable storage safety, media-type and backup-integrity checks."""

import asyncio
import hashlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from release_flow_support import entry, framework

from custom_components.media_bridge import backup_storage as storage


@pytest.mark.parametrize("name", ["../elsewhere", "/media/nas", "a/b", "", "nas space", "a\\b"])
def test_storage_names_cannot_escape_supervisor_media(name):
    with pytest.raises(ValueError):
        storage.storage_mount(name)


def test_mount_detection_requires_exact_writable_network_filesystem(monkeypatch):
    target = Path("/media/test_archives")
    monkeypatch.setattr(Path, "is_mount", lambda path: path == target)
    monkeypatch.setattr(Path, "is_symlink", lambda path: False)
    monkeypatch.setattr(Path, "resolve", lambda path: path)
    records = ["server:/export /media/test_archives nfs4 rw,relatime 0 0"]
    monkeypatch.setattr(Path, "read_text", lambda path, **kwargs: "\n".join(records))
    assert storage.network_filesystem(target) == "nfs4"
    records[0] = "//server/share /media/test_archives cifs rw,relatime 0 0"
    assert storage.network_filesystem(target) == "cifs"
    records[0] = "server:/export /media/test_archives nfs4 ro,relatime 0 0"
    assert storage.network_filesystem(target) is None
    records[0] = "/dev/sda1 /media/test_archives ext4 rw,relatime 0 0"
    assert storage.network_filesystem(target) is None
    records[0] = "server:/export /media nfs4 rw,relatime 0 0"
    assert storage.network_filesystem(target) is None


def test_missing_mount_and_symlink_escape_do_not_create_outside_directories(monkeypatch, tmp_path):
    mount, outside = tmp_path / "mount", tmp_path / "outside"
    mount.mkdir()
    outside.mkdir()
    monkeypatch.setattr(storage, "network_filesystem", lambda path: None)
    with pytest.raises(OSError):
        storage.safe_directory(mount, "blink", "front")
    assert list(mount.iterdir()) == []
    monkeypatch.setattr(storage, "network_filesystem", lambda path: "nfs4")
    (mount / "blink").symlink_to(outside, target_is_directory=True)
    with pytest.raises(OSError):
        storage.safe_directory(mount, "blink", "front")
    assert list(outside.iterdir()) == []


@pytest.mark.parametrize(
    "provider,media_type,extension",
    [
        ("blink", "video/mp2t", "ts"),
        ("blink", "video/mpeg", "mpegps"),
        ("ezviz", "video/mp2t", "ts"),
        ("ezviz", "video/mpeg", "mpegps"),
    ],
)
async def test_backup_preserves_actual_format_checksum_and_existing_file(
    monkeypatch, tmp_path, provider, media_type, extension
):
    env = framework(monkeypatch)
    backup = env.load("recording_backup")
    mount = tmp_path / "mounted"
    mount.mkdir()
    monkeypatch.setattr(storage, "network_filesystem", lambda path: "nfs4")
    monkeypatch.setattr(backup.shutil, "disk_usage", lambda path: SimpleNamespace(free=10**10))
    payload = b"bounded recording bytes"
    manifest = {
        "recording_id": "00000000-0000-4000-8000-000000000001",
        "camera": "front",
        "status": "ready",
        "media_type": media_type,
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }
    backup._validate(manifest, manifest["recording_id"], backup.MEDIA_EXTENSIONS)

    class Content:
        async def iter_chunked(self, size):
            yield payload

    upstream = SimpleNamespace(
        status=200, content_type=media_type, content=Content(), release=Mock()
    )
    result = await backup._backup(env.hass, provider, manifest, upstream, mount)
    target = mount / result["relative_path"]
    assert result["status"] == "created" and target.suffix == f".{extension}"
    assert target.read_bytes() == payload
    upstream.release.assert_called_once()
    assert (await backup._backup(env.hass, provider, manifest, upstream, mount))[
        "status"
    ] == "existing"
    other = {**manifest, "sha256": "0" * 64}
    with pytest.raises(OSError, match="different checksum"):
        backup._prepare(provider, other, mount)
    assert target.read_bytes() == payload


async def test_options_reconnect_does_not_require_enabling_backup(monkeypatch):
    env = framework(monkeypatch)
    module = env.load("options_flow")
    configured = entry("ezviz")
    configured.async_start_reauth = Mock()
    monkeypatch.setattr(
        module,
        "storage_readiness",
        lambda mount: {"ready": False, "reason": "network_mount_missing"},
    )
    flow = module.VistodaOptionsFlow()
    flow.config_entry, flow.hass = configured, env.hass
    result = await flow.async_step_init(
        {"backup_storage": "family_archive", "reconnect_account": True}
    )
    assert result["type"] == "create_entry"
    configured.async_start_reauth.assert_called_once_with(env.hass)
    result = await flow.async_step_init({"backup_storage": "new_missing_archive"})
    assert result["errors"]["base"] == "network_mount_missing"
    result = await flow.async_step_init({"backup_storage": "../../outside"})
    assert result["errors"]["base"] == "invalid_storage_name"


def test_readiness_is_redacted_and_reports_space(monkeypatch):
    monkeypatch.setattr(storage, "network_filesystem", lambda path: "cifs")
    monkeypatch.setattr(storage.os, "access", lambda *args: True)
    monkeypatch.setattr(storage.shutil, "disk_usage", lambda path: SimpleNamespace(free=100))
    result = storage.storage_readiness(Path("/media/private_house"))
    assert result == {"ready": False, "reason": "network_mount_low_space", "filesystem": "cifs"}
    assert "private_house" not in str(result)


@pytest.mark.parametrize("fault", ["checksum", "length", "mime", "cancel"])
async def test_invalid_stream_never_commits_a_backup(monkeypatch, tmp_path, fault):
    env = framework(monkeypatch)
    backup = env.load("recording_backup")
    monkeypatch.setattr(storage, "network_filesystem", lambda path: "nfs4")
    monkeypatch.setattr(backup.shutil, "disk_usage", lambda path: SimpleNamespace(free=10**10))
    payload = b"recording data"
    manifest = {
        "recording_id": "00000000-0000-4000-8000-000000000001",
        "camera": "front",
        "status": "ready",
        "media_type": "video/mp2t",
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }
    if fault == "checksum":
        manifest["sha256"] = "0" * 64
    if fault == "length":
        manifest["bytes"] = 1

    class Content:
        async def iter_chunked(self, size):
            if fault == "cancel":
                raise asyncio.CancelledError
            yield payload

    upstream = SimpleNamespace(
        status=200,
        content_type="text/plain" if fault == "mime" else "video/mp2t",
        content=Content(),
        release=Mock(),
    )
    with pytest.raises(asyncio.CancelledError if fault == "cancel" else ValueError):
        await backup._backup(env.hass, "ezviz", manifest, upstream, tmp_path)
    assert not [path for path in tmp_path.rglob("*") if path.is_file()]
    upstream.release.assert_called_once()
