"""HACS packaging, translation and maintenance gates."""

import json
from pathlib import Path

from scripts.check_loc import ROOT, maintained_files

COMPONENT = ROOT / "custom_components" / "media_bridge"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_manifest_and_hacs_metadata_are_consistent() -> None:
    manifest = load(COMPONENT / "manifest.json")
    hacs = load(ROOT / "hacs.json")
    constants = (COMPONENT / "const.py").read_text(encoding="utf-8")
    panel = (COMPONENT / "panel.py").read_text(encoding="utf-8")
    assert manifest["domain"] == "media_bridge"
    assert manifest["name"] == hacs["name"] == "Vistoda"
    assert manifest["config_flow"] is True
    assert manifest["version"] == "0.11.2"
    assert f'INTEGRATION_VERSION = "{manifest["version"]}"' in constants
    assert 'STATIC_ROOT = f"/vistoda_static/{INTEGRATION_VERSION}"' in panel
    assert 'STATIC_URL = f"{STATIC_ROOT}/vistoda-panel.js"' in panel
    assert "module_url=STATIC_URL" in panel
    assert manifest["zeroconf"] == ["_vistoda._tcp.local."]
    assert manifest["issue_tracker"].endswith("/vistoda-home-assistant/issues")
    assert hacs["homeassistant"] == "2026.8.0"


def test_translation_error_contracts_match() -> None:
    english = load(COMPONENT / "translations" / "en.json")
    italian = load(COMPONENT / "translations" / "it.json")
    source = load(COMPONENT / "strings.json")
    assert english["config"]["error"].keys() == italian["config"]["error"].keys()
    assert english["config"]["error"].keys() == source["config"]["error"].keys()


def test_config_flow_guidance_is_complete_in_every_language() -> None:
    documents = [
        load(COMPONENT / "strings.json"),
        load(COMPONENT / "translations" / "en.json"),
        load(COMPONENT / "translations" / "it.json"),
    ]
    required_fields = {
        "user": {"provider"},
        "bridge": {"url", "api_token", "alias"},
        "discovery_confirm": {"api_token"},
        "ring_credentials": {"email", "password"},
        "otp": {"code"},
        "ezviz_credentials": {"account", "password", "api_region"},
        "ezviz_otp": {"code"},
        "reconfigure": {"url", "api_token", "alias"},
    }
    for document in documents:
        assert document["title"] == "Vistoda"
        assert document["config"]["flow_title"] == "{name}"
        for step_name, fields in required_fields.items():
            step = document["config"]["step"][step_name]
            assert step["description"].strip()
            assert fields == step["data"].keys()
            assert fields == step["data_description"].keys()
        assert document["config"]["step"]["blink"]["description"].strip()
        assert set(document["selector"]["provider"]["options"]) == {
            "blink",
            "ezviz",
            "ring",
        }


def test_every_maintained_file_stays_within_250_lines() -> None:
    violations = []
    for path in maintained_files():
        count = len(path.read_text(encoding="utf-8").splitlines())
        if count > 250:
            violations.append(f"{path.relative_to(ROOT)}: {count}")
    assert not violations, "LOC budget exceeded:\n" + "\n".join(sorted(violations))


def test_repository_contains_no_secret_artifacts() -> None:
    forbidden_names = {"secrets.yaml", ".env", "token.json", "session.json"}
    assert not [path for path in ROOT.rglob("*") if path.name in forbidden_names]


def test_local_coordinator_supplies_the_ha_2026_logger_contract() -> None:
    source = (COMPONENT / "local.py").read_text(encoding="utf-8")
    assert "logger=_LOGGER" in source


def test_every_flow_path_supplies_required_translation_placeholders() -> None:
    source = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")
    managed = (COMPONENT / "managed_flow.py").read_text(encoding="utf-8")
    assert source.count("self._set_flow_title()") == 4
    assert "self._set_flow_title()" in managed
    assert 'self.context["title_placeholders"] = {"name": name}' in source
    assert 'description_placeholders={"provider": self._provider.upper()}' in source


def test_supervisor_apps_hide_bridge_fields_and_keep_external_mode() -> None:
    managed = (COMPONENT / "managed_flow.py").read_text(encoding="utf-8")
    flow = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")
    manifest = load(COMPONENT / "manifest.json")
    assert "async_step_hassio" in managed
    assert "CONF_MANAGED_APP: True" in managed
    assert "self._existing_provider_entry()" in managed
    assert "unique_id=self._unique_id()" in managed
    assert "reload_even_if_entry_is_unchanged=False" in managed
    assert "async_step_ring_credentials" in managed
    assert "async_step_ezviz_credentials" in managed
    assert "bridge_schema" in flow
    assert 'return self.async_abort(reason="managed_app")' in flow
    assert "hassio" not in manifest["dependencies"]


def test_unified_panel_has_private_authenticated_boundaries() -> None:
    manifest = load(COMPONENT / "manifest.json")
    panel = (COMPONENT / "frontend" / "vistoda-panel.js").read_text(encoding="utf-8")
    ring_view = (COMPONENT / "frontend" / "ring-view.js").read_text(encoding="utf-8")
    session = (COMPONENT / "frontend" / "ring-audio-session.js").read_text(encoding="utf-8")
    controls = (COMPONENT / "frontend" / "ring-controls.js").read_text(encoding="utf-8")
    recordings = (COMPONENT / "frontend" / "ring-recordings.js").read_text(encoding="utf-8")
    recorder = (COMPONENT / "frontend" / "ring-local-recorder.js").read_text(encoding="utf-8")
    websocket = (COMPONENT / "websocket.py").read_text(encoding="utf-8")
    recording_ws = (COMPONENT / "ring_recording_websocket.py").read_text(encoding="utf-8")
    assert {"http", "frontend", "panel_custom", "websocket_api"} <= set(manifest["dependencies"])
    assert "./overview-view.js" in panel
    assert "./blink-view.js" in panel
    assert "./ezviz-view.js" in panel
    assert "./ring-view.js" in panel
    assert "media_bridge/panel/info" in panel
    assert "Avvia comunicazione" in ring_view
    assert "Attiva microfono" in ring_view
    assert "vistoda-ring-recordings" in ring_view
    assert 'customElements.get("vistoda-panel")' in panel
    assert 'customElements.get("vistoda-ring-controls")' in controls
    assert 'customElements.get("vistoda-ring-recordings")' in recordings
    assert "Archivio chiamate" in recordings
    assert "Registra questa chiamata" in recordings
    assert "media_bridge/ring/recordings/upload" in recorder
    assert "MediaRecorder" in recorder
    assert "createMediaStreamDestination" in recorder
    assert "Call Recording" in recordings
    assert "non richiede" in recordings
    assert "Apri portone" in controls
    assert "Batteria" in controls
    assert "window.confirm" in controls
    assert 'callService("button", "press"' in controls
    assert 'callService("number", "set_value"' in controls
    assert "getUserMedia" in session
    assert "replaceTrack" in session
    assert 'direction: "sendrecv"' in session
    assert "media_bridge/ring/session/delete" in session
    assert "COOLDOWN_MS" in session
    assert "api_token" not in panel + ring_view
    assert "Authorization" not in panel + ring_view
    assert "api_token" not in session
    assert "Authorization" not in session
    assert "vol.Length(min=1, max=65536)" in websocket
    assert "media_bridge/ring/recordings/list" in recording_ws
    assert '"controls": controls' in websocket
    proxy = (COMPONENT / "ring_audio_proxy.py").read_text(encoding="utf-8")
    assert "requires_auth = True" in proxy
    assert 'PROXY_URL = "/api/media_bridge/ring/audio/{entry_id}"' in proxy
    assert "runtime.client.ring_relay(alias)" in proxy
    assert "Authorization" not in proxy
    callback = (COMPONENT / "apple_oauth_view.py").read_text(encoding="utf-8")
    assert "requires_auth = False" in callback
    assert "Cache-Control" in callback
    assert "native_callback" in callback
    apple_config = (COMPONENT / "apple_config_view.py").read_text(encoding="utf-8")
    assert "requires_auth = True" in apple_config
    assert '"open_door_service": f"{DOMAIN}.open_ring_door"' in apple_config
    assert "CONF_API_TOKEN" not in apple_config
    panel_registration = (COMPONENT / "panel.py").read_text(encoding="utf-8")
    assert 'PANEL_PATH = "vistoda"' in panel_registration
    assert '"vistoda-ring": ("ring"' in panel_registration
    assert '"vistoda-blink": ("blink"' in panel_registration
    assert '"vistoda-ezviz": ("ezviz"' in panel_registration
    assert "show_in_sidebar=False" in panel_registration


def test_panel_inventory_is_authenticated_bounded_and_secret_free() -> None:
    inventory = (COMPONENT / "panel_info.py").read_text(encoding="utf-8")
    websocket = (COMPONENT / "websocket.py").read_text(encoding="utf-8")
    assert '"media_bridge/panel/info"' in inventory
    assert "MAX_ENTITIES_PER_PROVIDER = 256" in inventory
    assert "entity.disabled_by is not None" in inventory
    assert "STATE_UNAVAILABLE" in inventory
    assert "async_register_panel_info(hass)" in websocket
    assert "api_token" not in inventory
    assert "CONF_URL" not in inventory
    assert "unique_id" not in inventory


def test_blink_and_ezviz_views_keep_expensive_actions_explicit() -> None:
    blink = (COMPONENT / "frontend" / "blink-view.js").read_text(encoding="utf-8")
    ezviz = (COMPONENT / "frontend" / "ezviz-view.js").read_text(encoding="utf-8")
    assert 'callService("blink_live_bridge", "trigger_camera"' in blink
    assert '"alarm_control_panel", armed ? "alarm_arm_away" : "alarm_disarm"' in blink
    assert 'openMoreInfo(this, this._current("camera")' in blink
    assert "Aggiorna snapshot" in blink
    assert "SceneTrove" in ezviz
    assert 'openMoreInfo(this, firstEntity(this._cameraDevice(), "camera")' in ezviz
    assert "api_token" not in blink + ezviz


def test_ring_door_service_is_vistoda_first_and_visible() -> None:
    service = (COMPONENT / "services.py").read_text(encoding="utf-8")
    definition = (COMPONENT / "services.yaml").read_text(encoding="utf-8")
    assert definition.startswith("open_ring_door:\n")
    assert 'SERVICE_OPEN_RING_DOOR = "open_ring_door"' in service
    assert "await runtime.client.ring_status(alias)" in service
    assert "await runtime.client.unlock_ring(alias)" in service
    assert '"official_fallback"' in service
    assert "outcome is unknown" in service
    assert "api_token" not in service


def test_ring_device_exposes_its_panel_and_audio_contract() -> None:
    sensor = (COMPONENT / "binary_sensor.py").read_text(encoding="utf-8")
    assert '"identifiers": {(DOMAIN, f"{provider}:{alias}")}' in sensor
    assert '_attr_name = "Audio Vistoda"' in sensor
    assert 'self._attr_device_info["configuration_url"]' in sensor
    assert 'attributes["panel_path"] = f"/vistoda-{self._provider}"' in sensor
    assert '"full_duplex": "true"' in sensor


def test_ring_facade_supports_native_and_official_control_paths() -> None:
    constants = (COMPONENT / "const.py").read_text(encoding="utf-8")
    facade = (COMPONENT / "ring_facade.py").read_text(encoding="utf-8")
    contract = (COMPONENT / "ring_contract.py").read_text(encoding="utf-8")
    button = (COMPONENT / "button.py").read_text(encoding="utf-8")
    event = (COMPONENT / "event.py").read_text(encoding="utf-8")
    assert '"button", "camera", "event", "number", "sensor"' in constants
    assert 'candidate.platform == "ring"' in contract
    assert 'candidate.manufacturer == "Ring"' in contract
    assert 'candidate.model == "Intercom"' in contract
    assert "await self.hass.services.async_call(" in facade
    assert 'await self.call_source_service("button", "press", {})' in button
    assert "await client.unlock_ring(self._alias)" in button
    assert "await client.set_ring_volume" in (COMPONENT / "number.py").read_text(encoding="utf-8")
    assert "never retry" in button
    assert "self._trigger_event(event_type, attributes)" in event
    assert "old_state.state == state.state" in event
    assert "timestamp_is_recent(state.state)" in event
    assert event.count("self.async_write_ha_state()") == 2
    assert "timestamps_match(restored.state, source.state)" in event
    assert "if restored is None or source is None:\n            return None" in event
