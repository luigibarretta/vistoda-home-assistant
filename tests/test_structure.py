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
    assert manifest["config_flow"] is True
    assert manifest["version"] == "0.1.0"
    assert hacs["homeassistant"] == "2026.8.0"


def test_translation_error_contracts_match() -> None:
    english = load(COMPONENT / "translations" / "en.json")
    italian = load(COMPONENT / "translations" / "it.json")
    source = load(COMPONENT / "strings.json")
    assert english["config"]["error"].keys() == italian["config"]["error"].keys()
    assert english["config"]["error"].keys() == source["config"]["error"].keys()


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
