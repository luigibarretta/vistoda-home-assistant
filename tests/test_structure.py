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
    assert manifest["version"] == "0.3.0"
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
