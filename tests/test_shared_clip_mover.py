"""Ready microSD clips move into SceneTrove's device folder, then leave the bridge."""

import hashlib
from types import SimpleNamespace
from unittest.mock import AsyncMock

from release_flow_support import framework

from custom_components.media_bridge import backup_storage as storage

ID = "0f1e2d3c-4b5a-6978-8a9b-0c1d2e3f4a5b"
LIVE = "1a2b3c4d-5e6f-4a1b-8c2d-3e4f5a6b7c8d"
MEDIA = b"\x00\x00\x01\xba" + b"clip" * 64
SD = {"recording_id": ID, "camera": "front-door", "status": "ready", "media_type": "video/mpeg",
      "source": "sd", "sd_start": 1793214000, "sd_end": 1793214060, "bytes": len(MEDIA),
      "sha256": hashlib.sha256(MEDIA).hexdigest()}  # fmt: skip
TS = {**SD, "recording_id": LIVE, "media_type": "video/mp2t", "source": None}
NAME = f"hiv20261028T190000Z-{ID}.mpegps"


class Upstream:
    status = 200
    content_type = "video/mpeg"

    def __init__(self, data):
        async def chunks(_size):
            yield data

        self.content = SimpleNamespace(iter_chunked=chunks)

    def release(self):
        pass


def mover_env(monkeypatch, tmp_path, *, manifest=SD, destination="shared"):
    env = framework(monkeypatch)
    env.load("recording_backup")
    module = env.load("shared_clip_mover")
    monkeypatch.setattr(storage, "network_filesystem", lambda path, **_: "nfs")
    monkeypatch.setattr(module, "storage_mount", lambda name: tmp_path / name)
    (tmp_path / "scenetrove_devices" / "spioncino").mkdir(parents=True)
    client = SimpleNamespace(
        provider_recordings=AsyncMock(return_value={"recordings": [SD, TS]}),
        provider_recording=AsyncMock(return_value=manifest),
        open_provider_recording=AsyncMock(return_value=Upstream(MEDIA)),
        delete_provider_recording=AsyncMock(),
    )
    options = {"scenetrove_url": "https://st.example", "scenetrove_device": "spioncino",
               "clip_destination": destination, "shared_storage": "scenetrove_devices"}  # fmt: skip
    entry = SimpleNamespace(data={"provider": "ezviz", "alias": "front-door"}, options=options)

    async def executor(function, *args):
        return function(*args)

    hass = SimpleNamespace(async_add_executor_job=executor)
    return module.SharedClipMover(hass, entry, client), client, tmp_path / "scenetrove_devices"


async def test_ready_microsd_clip_is_moved_then_deleted_on_the_bridge(monkeypatch, tmp_path):
    mover, client, shared = mover_env(monkeypatch, tmp_path)
    await mover.run()
    assert (shared / "spioncino" / NAME).read_bytes() == MEDIA
    assert (shared / "spioncino" / f"{NAME}.json").is_file()
    client.delete_provider_recording.assert_awaited_once_with(ID)


async def test_bridge_copy_is_kept_when_the_digest_differs(monkeypatch, tmp_path):
    mover, client, shared = mover_env(monkeypatch, tmp_path, manifest={**SD, "sha256": "0" * 64})
    await mover.run()
    assert not (shared / "spioncino" / NAME).exists()
    client.delete_provider_recording.assert_not_awaited()


async def test_live_ts_recordings_are_left_alone(monkeypatch, tmp_path):
    mover, client, _shared = mover_env(monkeypatch, tmp_path)
    await mover.run()
    assert [call.args[0] for call in client.provider_recording.await_args_list] == [ID]


async def test_nothing_moves_without_sharing(monkeypatch, tmp_path):
    mover, client, _shared = mover_env(monkeypatch, tmp_path, destination="vistoda")
    await mover.run()
    client.provider_recordings.assert_not_awaited()
