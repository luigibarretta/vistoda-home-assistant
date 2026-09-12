"""Protect the public authorship, independence and accessibility surface."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "custom_components" / "media_bridge" / "frontend"


def test_about_dialog_is_accessible_and_does_not_use_vendor_brand_assets() -> None:
    dialog = (FRONTEND / "vistoda-about-dialog.js").read_text(encoding="utf-8")
    panel = (FRONTEND / "vistoda-panel.js").read_text(encoding="utf-8")
    assert 'aria-labelledby="about-title"' in dialog
    assert 'aria-describedby="about-summary"' in dialog
    assert 'rel="noopener noreferrer"' in dialog
    assert "https://github.com/luigibarretta" in dialog
    assert "https://ko-fi.com/luigibarretta" in dialog
    assert "ACCESSIBILITY.md" in dialog and "DISCLAIMER.md" in dialog
    assert "mdi:information-outline" in panel
    assert 'import "./vistoda-about-dialog.js"' in panel
    assert all(
        f"mdi:{vendor}" not in dialog.lower() for vendor in ("ring", "blink", "ezviz", "amazon")
    )


def test_accessibility_statement_is_honest_and_bilingual() -> None:
    english = (ROOT / "ACCESSIBILITY.md").read_text(encoding="utf-8")
    italian = (ROOT / "ACCESSIBILITY.it.md").read_text(encoding="utf-8")
    assert "WCAG 2.2 Level AA" in english
    assert "does not yet claim formal WCAG conformance" in english
    assert "non dichiara ancora una conformità WCAG formale" in italian
    assert "Chromium, Firefox and WebKit" in english
    assert english.count("\n## ") == italian.count("\n## ")


def test_disclaimer_is_visible_without_changing_repository_licenses() -> None:
    english = (ROOT / "DISCLAIMER.md").read_text(encoding="utf-8")
    italian = (ROOT / "DISCLAIMER.it.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "not affiliated with, sponsored, authorized or endorsed" in english
    assert "Non è affiliato, sponsorizzato, autorizzato o approvato" in italian
    assert "does not replace or modify a repository license" in english
    assert "DISCLAIMER.md" in readme and "ACCESSIBILITY.md" in readme
