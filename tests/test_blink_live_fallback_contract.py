"""Static safety boundary for Blink Cayuga-to-Walnut fallback."""

from pathlib import Path

FRONTEND = Path(__file__).parents[1] / "custom_components/media_bridge/frontend"


def test_blink_fallback_is_typed_one_way_and_releases_webrtc_first() -> None:
    source = (FRONTEND / "blink-live-session.js").read_text(encoding="utf-8")
    assert 'state.phase === "fallback"' in source
    assert 'legacyAvailable: state.phase === "error"' in source
    assert "this.fallbackUsed = true" in source
    assert source.index("await webRtc.stop(false)") < source.index("await legacy.start")


def test_blink_official_policy_selects_walnut_before_signaling() -> None:
    session = (FRONTEND / "blink-live-session.js").read_text(encoding="utf-8")
    view = (FRONTEND / "blink-view-live.js").read_text(encoding="utf-8")
    assert 'preferredTransport = "walnut"' in session
    assert 'preferredTransport !== "cayuga"' in session
    start = session.split("async start(alias", 1)[1]
    assert start.index('preferredTransport !== "cayuga"') < start.index("this.makeWebRtc")
    assert 'camera.attributes.preferred_live_transport === "cayuga"' in view
    assert '? "cayuga" : "walnut"' in view


def test_blink_legacy_player_uses_home_assistant_without_vendor_secrets() -> None:
    source = (FRONTEND / "blink-legacy-live-session.js").read_text(encoding="utf-8")
    assert "loadHaCardHelpers" in source
    assert 'camera_view: "live"' in source
    assert "api_token" not in source
