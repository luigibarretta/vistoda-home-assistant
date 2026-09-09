"""Static contracts for the Vistoda Blink camera settings experience."""

from pathlib import Path

ROOT = Path(__file__).parents[1]
FRONTEND = ROOT / "custom_components/media_bridge/frontend"


def test_blink_settings_use_the_authenticated_typed_websocket_boundary() -> None:
    settings = (FRONTEND / "blink-settings.js").read_text(encoding="utf-8")
    view = (FRONTEND / "blink-view.js").read_text(encoding="utf-8")
    assert "blink_live_bridge/camera/settings" in settings
    assert "key: field.key, value, revision: this._settings.revision" in settings
    assert "connection" not in settings
    assert "api_token" not in settings + view
    assert "Authorization" not in settings + view
    assert "Registra clip" in view


def test_blink_settings_present_provider_values_as_states_not_actions() -> None:
    settings = (FRONTEND / "blink-settings.js").read_text(encoding="utf-8")
    model = (FRONTEND / "blink-setting-model.js").read_text(encoding="utf-8")
    assert 'button.setAttribute("aria-checked", String(field.value))' in settings
    assert "booleanStateText(field.value)" in settings
    assert 'return value === true ? "Attivata" : "Disattivata"' in model
    assert 'field.value ? "Attiva" : "Spenta"' not in settings


def test_video_quality_uses_described_radio_choices() -> None:
    settings = (FRONTEND / "blink-settings.js").read_text(encoding="utf-8")
    model = (FRONTEND / "blink-setting-model.js").read_text(encoding="utf-8")
    assert 'input.type = "radio"' in settings
    assert "Standard (consigliata)" in model
    assert "almeno 3 Mbps" in model
    assert "almeno 2 Mbps" in model
    assert "almeno 500 Kbps" in model


def test_model_aware_blink_controls_have_native_labels() -> None:
    settings = (FRONTEND / "blink-settings.js").read_text(encoding="utf-8")
    for key in (
        "flip_video",
        "photo_capture",
        "auto_thumbnail",
        "status_led",
        "speaker_volume",
        "sync_strength",
        "camera_name",
    ):
        assert key in settings
    assert 'medium: "Media"' in settings
    assert 'recording: "Durante la registrazione"' in settings
    assert 'if (field.kind === "text")' in settings


def test_blink_paginator_draws_round_dots_inside_touch_targets() -> None:
    styles = (FRONTEND / "panel-styles.js").read_text(encoding="utf-8")
    view = (FRONTEND / "blink-view.js").read_text(encoding="utf-8")
    assert ".pager button.dot" in styles
    assert '.dot::before { content:""; width:8px; height:8px; border-radius:50%' in styles
    assert 'button.setAttribute("aria-current", "true")' in view


def test_provider_links_are_nested_but_legacy_routes_remain_registered() -> None:
    panel = (FRONTEND / "vistoda-panel.js").read_text(encoding="utf-8")
    helpers = (FRONTEND / "panel-helpers.js").read_text(encoding="utf-8")
    registration = (ROOT / "custom_components/media_bridge/panel.py").read_text(encoding="utf-8")
    assert "providerPath(provider)" in panel
    assert 'return provider === "overview" ? "/vistoda" : `/vistoda/${provider}`' in helpers
    assert "canonicalVistodaPath" in panel
    assert '"vistoda-blink": ("blink"' in registration
