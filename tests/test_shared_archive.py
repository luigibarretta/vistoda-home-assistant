"""The archive shared with SceneTrove: clip names and the options that turn it on."""

from release_flow_support import framework
from test_event_archive_options import options_flow

ID = "0f1e2d3c-4b5a-6978-8a9b-0c1d2e3f4a5b"
SD_CLIP = {"recording_id": ID, "media_type": "video/mpeg", "source": "sd", "sd_start": 1793214000}
BASE = {"backup_storage": "family_archive", "event_archive": False, "event_retention_days": 0}
LINKED = {**BASE, "scenetrove_url": "https://st.example", "scenetrove_device": "spioncino"}


def test_shared_clip_names_follow_scenetrove(monkeypatch):
    module = framework(monkeypatch).load("shared_archive")
    assert module.shared_clip_name(SD_CLIP) == f"hiv20261028T190000Z-{ID}.mpegps"
    for other in (
        {**SD_CLIP, "media_type": "video/mp2t"},
        {**SD_CLIP, "source": None},
        {**SD_CLIP, "recording_id": "../escape"},
        {**SD_CLIP, "recording_id": ID.upper()},
    ):
        assert module.shared_clip_name(other) is None, other


async def test_vistoda_is_the_default_destination(monkeypatch):
    result = await options_flow(monkeypatch).async_step_init(LINKED)
    assert result["data"]["clip_destination"] == "vistoda"


async def test_shared_mode_needs_a_link_and_ready_storage(monkeypatch):
    shared = {"clip_destination": "shared", "shared_storage": "scenetrove_devices"}
    flow = options_flow(monkeypatch)
    unlinked = await flow.async_step_init({**BASE, **shared})
    assert unlinked["errors"] == {"base": "shared_needs_scenetrove"}
    saved = await flow.async_step_init({**LINKED, **shared})
    assert saved["data"]["clip_destination"] == "shared"
    assert saved["data"]["shared_storage"] == "scenetrove_devices"
    missing = await options_flow(monkeypatch, ready=False).async_step_init({**LINKED, **shared})
    assert missing["errors"] == {"base": "network_mount_missing"}
