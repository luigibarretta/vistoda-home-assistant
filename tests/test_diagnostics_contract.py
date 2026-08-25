"""Diagnostics and Repairs packaging contracts."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "media_bridge"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_diagnostics_and_repairs_are_secret_free_and_native() -> None:
    diagnostics = (COMPONENT / "diagnostics.py").read_text(encoding="utf-8")
    repairs = (COMPONENT / "repairs.py").read_text(encoding="utf-8")
    coordinator = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
    assert "async_get_config_entry_diagnostics" in diagnostics
    assert "async_redact_data" in diagnostics
    assert "TO_REDACT = {CONF_ALIAS, CONF_API_TOKEN, CONF_URL}" in diagnostics
    assert "async_create_issue" in repairs
    assert "async_delete_issue" in repairs
    assert "translation_placeholders" in repairs
    assert "update_bridge_issue" in coordinator
    assert "update_ring_push_issue" in repairs
    assert 'payload["ring_events"]' in diagnostics


def test_repair_translations_match() -> None:
    source = load(COMPONENT / "strings.json")
    english = load(COMPONENT / "translations/en.json")
    italian = load(COMPONENT / "translations/it.json")
    assert english["issues"].keys() == italian["issues"].keys() == source["issues"].keys()


def test_ring_events_prefer_native_push_with_fallback() -> None:
    event = (COMPONENT / "event.py").read_text(encoding="utf-8")
    listener = (COMPONENT / "ring_event_listener.py").read_text(encoding="utf-8")
    assert "ring_event_signal" in event
    assert '"source": "vistoda_native"' in event
    assert "self.client.ring_events" in listener
    assert "RingEventCursor" in listener
    assert "failures >= 6" in listener
    assert "update_ring_push_issue" in listener
    assert "EVENT_HOMEASSISTANT_STOP" in listener
    assert "await self.stop()" in listener
