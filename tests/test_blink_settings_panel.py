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
