"""Wire fixture matches Ring's executable addon_multidevice wrapper contract."""

import json
from pathlib import Path

import pytest

from custom_components.media_bridge.managed_devices import discovered_devices


def test_ring_wrapper_discovery_preserves_string_physical_ids():
    fixture = Path(__file__).parent / "fixtures" / "ring-managed-discovery.json"
    config = json.loads(fixture.read_text())["config"]
    assert discovered_devices(config) == [
        {"alias": "intercom-41", "ring_device_id": "41"},
        {"alias": "intercom-42", "ring_device_id": "42"},
    ]
    config["devices"][0]["device_id"] = 41
    with pytest.raises(ValueError, match="identity"):
        discovered_devices(config)
