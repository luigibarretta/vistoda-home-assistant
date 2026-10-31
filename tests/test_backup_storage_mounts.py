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
