"""Static contracts for the Vistoda Blink camera settings experience."""

from pathlib import Path

ROOT = Path(__file__).parents[1]
FRONTEND = ROOT / "custom_components/media_bridge/frontend"


def test_blink_settings_use_the_authenticated_typed_websocket_boundary() -> None:
    settings = (FRONTEND / "blink-settings.js").read_text(encoding="utf-8")
    draft = (FRONTEND / "blink-setting-draft.js").read_text(encoding="utf-8")
    view = (FRONTEND / "blink-view.js").read_text(encoding="utf-8")
    template = (FRONTEND / "blink-view-template.js").read_text(encoding="utf-8")
    assert "blink_live_bridge/camera/settings" in settings
    assert 'type: "blink_live_bridge/camera/settings/update"' in draft
    assert "alias, key, value, revision: current.revision" in draft
    assert "connection" not in settings
    assert "api_token" not in settings + draft + view
    assert "Authorization" not in settings + draft + view
    assert "vistoda-provider-recordings" in template
    assert "Registra clip" not in template


def test_blink_settings_present_provider_values_as_states_not_actions() -> None:
    settings = (FRONTEND / "blink-settings.js").read_text(encoding="utf-8")
    model = (FRONTEND / "blink-setting-model.js").read_text(encoding="utf-8")
    assert 'button.setAttribute("aria-checked", String(field.value))' in settings
    assert "booleanStateText(field.value, this)" in settings
    assert 'copy(context, value === true ? "Attivata" : "Disattivata")' in model
    assert 'field.value ? "Attiva" : "Spenta"' not in settings


def test_blink_settings_stage_one_confirmed_batch_and_show_ha_temperature_unit() -> None:
    settings = (FRONTEND / "blink-settings.js").read_text(encoding="utf-8")
    draft = (FRONTEND / "blink-setting-draft.js").read_text(encoding="utf-8")
    model = (FRONTEND / "blink-setting-model.js").read_text(encoding="utf-8")
    assert "Salva modifiche" in settings
    assert 'copy(this, "Confermi {p0} {p1} a questa telecamera?"' in settings
    assert "commitDraft" in settings and "applied.reverse()" in draft
    assert "temperatureValueText" in settings
    assert "unit_system?.temperature" in model


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
    schema = (FRONTEND / "blink-setting-schema.js").read_text(encoding="utf-8")
    for key in (
        "flip_video",
        "photo_capture",
        "auto_thumbnail",
        "status_led",
        "speaker_volume",
        "sync_strength",
        "camera_name",
    ):
        assert key in schema
    assert 'medium: "Media"' in schema
    assert 'recording: "Durante la registrazione"' in schema
    assert 'if (field.kind === "text")' in settings


def test_blink_settings_use_five_single_open_accordions_and_embed_zones() -> None:
    settings = (FRONTEND / "blink-settings.js").read_text(encoding="utf-8")
    schema = (FRONTEND / "blink-setting-schema.js").read_text(encoding="utf-8")
    template = (FRONTEND / "blink-view-template.js").read_text(encoding="utf-8")
    styles = (FRONTEND / "blink-setting-styles.js").read_text(encoding="utf-8")
    assert schema.count('key: "') == 5
    for title in (
        "Impostazioni generali",
        "Impostazioni movimento",
        "Impostazioni video e foto",
        "Impostazioni audio",
        "Impostazioni privacy",
    ):
        assert title in schema
    assert '<details class="setting-section"' in settings
    assert "_keepSingleSectionOpen" in settings
    assert '<slot name="zones"></slot>' in settings
    assert 'slot="zones"' in template and "embedded" in template
    assert "details[open] .chevron" in styles
    panel_styles = (FRONTEND / "panel-styles.js").read_text(encoding="utf-8")
    assert "[hidden] { display:none !important; }" in panel_styles


def test_blink_pager_arrows_have_accessible_names_without_hover_tooltips() -> None:
    template = (FRONTEND / "blink-view-template.js").read_text(encoding="utf-8")
    assert 'id="previous"\n  aria-label="Telecamera precedente">' in template
    assert 'id="next" aria-label="Telecamera successiva">' in template
    assert "Mostra la telecamera precedente" not in template
    assert "Mostra la telecamera successiva" not in template


def test_blink_paginator_draws_round_dots_inside_touch_targets() -> None:
    styles = (FRONTEND / "panel-styles.js").read_text(encoding="utf-8")
    view = (FRONTEND / "blink-view.js").read_text(encoding="utf-8")
    assert ".pager button.dot" in styles
    assert '.dot::before { content:""; width:8px; height:8px; border-radius:50%' in styles
    assert 'button.setAttribute("aria-current", "true")' in view


def test_blink_usb_archive_is_guarded_and_uses_signed_downloads() -> None:
    storage = "\n".join(
        (FRONTEND / name).read_text(encoding="utf-8")
        for name in (
            "blink-storage.js",
            "blink-storage-actions.js",
            "blink-storage-template.js",
        )
    )
    template = (FRONTEND / "blink-view-template.js").read_text(encoding="utf-8")
    assert 'type: "blink_live_bridge/local_storage/list"' in storage
    assert 'type: "auth/sign_path"' in storage
    assert "/api/blink_live_bridge/v1/local-storage/" in storage
    assert "Riproduci" in storage and "Backup archivio Blink" in storage
    assert "media_bridge/blink/usb/backup" in storage
    assert "page_size" in storage and "Pagina" in storage
    assert "vistoda-blink-storage" in template
    assert "local_storage/delete" in storage and "local_storage/format" in storage
    assert "FORMATTA ${storage.network_id}/${storage.sync_module_id}" in storage
    assert "Spazio disponibile:" in storage and "Spazio occupato:" not in storage
    assert "local_storage/eject" not in storage and "local_storage/mount" not in storage


def test_blink_zone_editor_uses_typed_native_grid_and_admin_boundary() -> None:
    settings = (FRONTEND / "blink-settings.js").read_text(encoding="utf-8")
    zones = (FRONTEND / "blink-zones.js").read_text(encoding="utf-8")
    model = (FRONTEND / "blink-zone-model.js").read_text(encoding="utf-8")
    styles = (FRONTEND / "blink-zone-styles.js").read_text(encoding="utf-8")
    view = (FRONTEND / "blink-view.js").read_text(encoding="utf-8")
    template = (FRONTEND / "blink-view-template.js").read_text(encoding="utf-8")
    assert "blink_live_bridge/camera/zones" in zones
    assert "blink_live_bridge/camera/zones/update" in zones
    assert "activity_masks: this._masks, privacy_zones: this._privacy" in zones
    assert "GRID_COLUMNS = 20" in model and "GRID_ROWS = 15" in model
    assert "aspect-ratio:16/9" in styles
    assert "vistoda-blink-zones" in template
    assert 'id="details-page"' in template
    assert "Dettagli e impostazioni" in template
    assert "modello. Zone," not in settings
    assert "Authorization" not in zones + view


def test_provider_links_are_nested_but_legacy_routes_remain_registered() -> None:
    panel = (FRONTEND / "vistoda-panel.js").read_text(encoding="utf-8")
    helpers = (FRONTEND / "panel-helpers.js").read_text(encoding="utf-8")
    registration = (ROOT / "custom_components/media_bridge/panel.py").read_text(encoding="utf-8")
    assert "providerPath(provider)" in panel
    assert 'return provider === "overview" ? "/vistoda" : `/vistoda/${provider}`' in helpers
    assert "canonicalVistodaPath" in panel
    assert '"vistoda-blink": ("blink"' in registration
