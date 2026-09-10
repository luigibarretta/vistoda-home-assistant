"""Accessible icon-and-label controls for Vistoda camera panels."""

from pathlib import Path

FRONTEND = Path("custom_components/media_bridge/frontend")


def source(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


def test_blink_primary_controls_expose_state_icons_and_text() -> None:
    template = source("blink-view-template.js")
    view = source("blink-view.js")
    live = source("blink-view-live.js")
    for icon in (
        "mdi:video-wireless-outline",
        "mdi:camera-retake-outline",
        "mdi:motion-sensor",
        "mdi:cog-outline",
        "mdi:battery",
        "mdi:thermometer",
        "mdi:video-box",
    ):
        assert icon in template
    assert "mdi:motion-sensor-off" in view
    assert "mdi:microphone-off" in template and "mdi:microphone" in live
    assert "mdi:volume-off" in template and "mdi:volume-high" in live


def test_usb_facts_are_vertically_centered_icon_labels() -> None:
    storage = source("blink-storage.js")
    styles = source("blink-storage-styles.js")
    assert all(icon in storage for icon in (
        "mdi:usb-flash-drive", "mdi:harddisk", "mdi:cloud-check-outline"))
    assert ".module-facts { display:flex; align-items:center" in styles
    assert ".storage-fact { display:inline-flex; align-items:center" in styles


def test_ezviz_and_archive_actions_keep_labels_with_icons() -> None:
    ezviz = source("ezviz-view.js")
    archive = source("provider-recordings-template.js")
    assert "mdi:lan-connect" in ezviz and "mdi:camera-retake-outline" in ezviz
    assert "mdi:record-rec" in archive and "Registra live" in archive
    assert "mdi:chevron-left" in archive and "mdi:chevron-right" in archive


def test_blink_webrtc_controls_are_accessible_and_race_guarded() -> None:
    live = source("blink-view-live.js")
    session = source("blink-webrtc-session.js")
    microphone = source("blink-webrtc-microphone.js")
    ring = source("ring-audio-session.js")
    assert "openMoreInfo" in live and "is_admin !== true" in live
    assert 'setAttribute("aria-busy"' in live
    assert "generation !== this.generation" in session + microphone
    assert "performance.now() < this.micCooldownUntil" in microphone
    assert "MAX_ICE_CANDIDATES" in session
    assert "connectionChanged(pc, generation)" in ring
