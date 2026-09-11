"""Manual EZVIZ snapshot cache and UI contracts."""

from pathlib import Path

import pytest

from custom_components.media_bridge.ezviz_snapshot_cache import _load, _save


def test_snapshot_cache_round_trip_is_complete_and_private(tmp_path: Path) -> None:
    image_path = tmp_path / ".storage" / "snapshot.jpg"
    metadata_path = tmp_path / ".storage" / "snapshot.json"
    image = b"\xff\xd8bounded-jpeg\xff\xd9"
    updated_at = "2026-09-10T12:00:00+00:00"

    _save(image_path, metadata_path, image, updated_at)

    assert _load(image_path, metadata_path) == (image, updated_at)
    assert not image_path.with_suffix(".jpg.tmp").exists()
    assert not metadata_path.with_suffix(".json.tmp").exists()


@pytest.mark.parametrize("image", (b"", b"not-jpeg", b"\xff\xd8truncated"))
def test_snapshot_cache_rejects_incomplete_images(tmp_path: Path, image: bytes) -> None:
    image_path = tmp_path / "snapshot.jpg"
    metadata_path = tmp_path / "snapshot.json"
    image_path.write_bytes(image)
    metadata_path.write_text('{"updated_at":"2026-09-10T12:00:00+00:00"}')

    assert _load(image_path, metadata_path) == (None, None)


def test_ezviz_provider_fetch_happens_only_after_explicit_websocket_action() -> None:
    component = Path("custom_components/media_bridge")
    camera = (component / "camera.py").read_text()
    websocket = (component / "provider_recording_websocket.py").read_text()
    view = (component / "frontend" / "ezviz-view.js").read_text()

    assert "client.snapshot" not in camera
    assert "runtime.client.snapshot(alias)" in websocket
    assert 'type: "media_bridge/ezviz/snapshot/refresh"' in view
    assert "this._nonce = 0" in view
    assert "this._snapshotObservedAt = Date.now()" not in view
    assert "this._snapshotTimes.set(cameraId, Date.parse(result.updated_at)" in view
    assert "Ultimo snapshot salvato disponibile" in view
