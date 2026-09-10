"""Structural release gates for Ring event history."""

from pathlib import Path

COMPONENT = Path("custom_components/media_bridge")


def test_ring_history_is_persisted_paginated_and_has_a_mobile_subpage() -> None:
    client = (COMPONENT / "client_ring_history.py").read_text(encoding="utf-8")
    history = (COMPONENT / "ring_history.py").read_text(encoding="utf-8")
    websocket = (COMPONENT / "ring_history_websocket.py").read_text(encoding="utf-8")
    frontend = (COMPONENT / "frontend" / "ring-history.js").read_text(encoding="utf-8")
    identity = (COMPONENT / "frontend" / "ring-identity-dialog.js").read_text(encoding="utf-8")
    view = (COMPONENT / "frontend" / "ring-view.js").read_text(encoding="utf-8")
    assert "\"/v1/devices/{quote(alias, safe='')}/history\"" in client
    assert 'EVENT_RING_UNLOCKED = "vistoda_ring_entry_unlocked"' in history
    assert 'f"{DOMAIN}.ring_history.{entry.entry_id}"' in history
    assert '"media_bridge/ring/history"' in websocket
    assert "Carica eventi precedenti" in frontend
    assert "Cronologia eventi" in view
    assert "mdi:lock-open-outline" in frontend
    assert "media_bridge/ring/identity/update" in identity
    assert "Home Assistant espone" in identity


def test_ring_identity_uses_the_supported_device_registry_lookup() -> None:
    identity = (COMPONENT / "ring_identity.py").read_text(encoding="utf-8")
    assert "async_get_device_by_identifier" in identity
    assert "async_get_device(" not in identity
