"""Network mount detection: exact destination, network filesystem, rw only for writes."""

from custom_components.media_bridge.backup_storage import mount_filesystem

MOUNTS = (
    "server:/export /media/vistoda_archives nfs4 rw,relatime 0 0\n"
    "server:/ro /media/read_only nfs ro,relatime 0 0\n"
    "/dev/sda1 /media/local ext4 rw 0 0\n"
    "server:/x /media/with\\040space cifs rw 0 0\n"
)


def test_writes_need_a_read_write_network_mount():
    assert mount_filesystem(MOUNTS, "/media/vistoda_archives") == "nfs4"
    assert mount_filesystem(MOUNTS, "/media/read_only") is None
    assert mount_filesystem(MOUNTS, "/media/local") is None
    assert mount_filesystem(MOUNTS, "/media/with space") == "cifs"


def test_reads_accept_a_read_only_network_mount():
    assert mount_filesystem(MOUNTS, "/media/read_only", writable=False) == "nfs"
    assert mount_filesystem(MOUNTS, "/media/local", writable=False) is None


# --- Choosing where backups go: a folder (or sub-folder) below /media ---

from types import SimpleNamespace  # noqa: E402

import pytest  # noqa: E402

from custom_components.media_bridge import backup_storage  # noqa: E402


@pytest.fixture
def media(tmp_path, monkeypatch):
    root = tmp_path.resolve() / "media"
    root.mkdir()
    monkeypatch.setattr(backup_storage, "MEDIA_ROOT", root)
    monkeypatch.setattr(backup_storage, "MIN_FREE_BYTES", 0)
    monkeypatch.setattr(backup_storage, "_LOCAL_DESTINATIONS", set())
    return root


def test_storage_name_may_be_a_short_path_of_plain_names(media):
    assert backup_storage.storage_mount("vistoda_archives") == media / "vistoda_archives"
    assert backup_storage.storage_mount("blink/clips") == media / "blink" / "clips"
    assert backup_storage.storage_mount("a/b/c/d") == media / "a" / "b" / "c" / "d"


@pytest.mark.parametrize(
    "name", ["", "/etc", "../x", "a/../b", "a/./b", "a//b", ".hidden", "a/b/c/d/e", "a b", None]
)
def test_storage_name_rejects_anything_that_could_leave_media(media, name):
    with pytest.raises(ValueError):
        backup_storage.storage_mount(name)


def test_local_folder_is_refused_until_the_user_opts_in(media):
    mount = backup_storage.storage_mount("blink/clips")
    backup_storage.prepare_local_destination(mount)
    assert mount.is_dir()
    assert backup_storage.network_filesystem(mount) is None
    assert backup_storage.storage_readiness(mount)["reason"] == "network_mount_missing"

    backup_storage.allow_local_destination(mount, True)
    assert backup_storage.network_filesystem(mount) == "local"
    assert backup_storage.storage_readiness(mount)["ready"] is True

    backup_storage.allow_local_destination(mount, False)
    assert backup_storage.network_filesystem(mount) is None


def test_opt_in_never_accepts_symlinks_or_missing_folders(media, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    link = media / "link"
    link.symlink_to(outside)
    missing = backup_storage.storage_mount("nowhere")
    backup_storage.allow_local_destination(link, True)
    backup_storage.allow_local_destination(missing, True)
    assert backup_storage.network_filesystem(link) is None
    assert backup_storage.network_filesystem(missing) is None


def test_prepare_refuses_paths_outside_media_and_symlinked_parents(media, tmp_path):
    from pathlib import Path

    with pytest.raises(OSError):
        backup_storage.prepare_local_destination(Path("/tmp/elsewhere"))
    with pytest.raises(OSError):
        backup_storage.prepare_local_destination(media)
    outside = tmp_path / "outside"
    outside.mkdir()
    (media / "link").symlink_to(outside)
    with pytest.raises(OSError):
        backup_storage.prepare_local_destination(media / "link" / "sub")
    assert not (outside / "sub").exists()


def test_configured_mount_applies_the_entry_option(media):
    entry = SimpleNamespace(options={"backup_storage": "blink/clips", "backup_allow_local": True})
    mount = backup_storage.configured_mount(entry)
    backup_storage.prepare_local_destination(mount)
    assert backup_storage.network_filesystem(mount) == "local"
