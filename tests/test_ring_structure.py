"""Static Ring facade and entity contract checks."""

from scripts.check_loc import ROOT

COMPONENT = ROOT / "custom_components" / "media_bridge"


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
    assert "await client.unlock_ring(self._alias, expected_device_id=expected_device_id)" in button
    number = (COMPONENT / "number.py").read_text(encoding="utf-8")
    assert "await client.set_ring_volume" in number
    assert "self._trigger_event(event_type, attributes)" in event
    assert "old_state.state == state.state" in event
    assert "timestamp_is_recent(state.state)" in event
    assert event.count("self.async_write_ha_state()") >= 3
    assert "Never replay a restored call" in event
