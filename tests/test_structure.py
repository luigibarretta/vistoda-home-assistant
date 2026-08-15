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
    assert manifest["domain"] == "media_bridge"
    assert manifest["name"] == hacs["name"] == "Vistoda"
    assert manifest["config_flow"] is True
    assert manifest["version"] == "0.4.2"
    assert manifest["zeroconf"] == ["_vistoda._tcp.local."]
    assert manifest["issue_tracker"].endswith("/home-assistant-media-bridge/issues")
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
    assert source.count("self._set_flow_title()") == 4
    assert 'self.context["title_placeholders"] = {"name": name}' in source
    assert 'description_placeholders={"provider": self._provider.upper()}' in source


def test_ring_panel_has_private_authenticated_boundaries() -> None:
    manifest = load(COMPONENT / "manifest.json")
    panel = (COMPONENT / "frontend" / "vistoda-panel.js").read_text(encoding="utf-8")
    session = (COMPONENT / "frontend" / "ring-audio-session.js").read_text(encoding="utf-8")
    websocket = (COMPONENT / "websocket.py").read_text(encoding="utf-8")
    assert {"frontend", "panel_custom", "websocket_api"} <= set(manifest["dependencies"])
    assert "Vistoda · Ring" in panel
    assert "Parla e ascolta" in panel
    assert "getUserMedia" in session
    assert "replaceTrack" in session
    assert 'direction: "sendrecv"' in session
    assert "media_bridge/ring/session/delete" in session
    assert "COOLDOWN_MS" in session
    assert "api_token" not in panel
    assert "Authorization" not in panel
    assert "api_token" not in session
    assert "Authorization" not in session
    assert "vol.Length(min=1, max=65536)" in websocket


def test_ring_device_exposes_its_panel_and_audio_contract() -> None:
    sensor = (COMPONENT / "binary_sensor.py").read_text(encoding="utf-8")
    assert '"identifiers": {(DOMAIN, f"{provider}:{alias}")}' in sensor
    assert '_attr_name = "Audio Vistoda"' in sensor
    assert 'self._attr_device_info["configuration_url"]' in sensor
    assert '"panel_path": "/vistoda-ring"' in sensor
    assert '"full_duplex": "true"' in sensor
