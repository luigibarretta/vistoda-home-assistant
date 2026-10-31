"""EZVIZ platform setup: which entities exist before optional app routes answer."""

import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock

from ha_stub_support import load

from custom_components.media_bridge.client_ezviz_media import EzvizStorage
from tests.test_ezviz_media_runtime import ezviz_entry, stub_modules


async def test_platforms_defer_optional_entities_until_supported(monkeypatch) -> None:
    stub_modules(monkeypatch)
    sensor_module = sys.modules["homeassistant.components.sensor"]
    sensor_module.SensorDeviceClass = SimpleNamespace(
        ENUM="enum", BATTERY="battery", TIMESTAMP="timestamp"
    )
    sensor_module.SensorStateClass = SimpleNamespace(MEASUREMENT="measurement")
    util = ModuleType("homeassistant.util")
    util.dt = sys.modules["homeassistant.util.dt"]
    monkeypatch.setitem(sys.modules, util.__name__, util)
    media = load(monkeypatch, "ezviz_media")
    sensor = load(monkeypatch, "sensor")
    binary = load(monkeypatch, "binary_sensor")
    listeners = []
    coordinator = SimpleNamespace(data=None, last_update_success=True, async_refresh=Mock())
    coordinator.async_add_listener = lambda listener: listeners.append(listener) or Mock()
    runtime = SimpleNamespace(
        ezviz_media=coordinator, coordinator=coordinator, ring_status=None, panel_url=None
    )
    entry = ezviz_entry()
    entry.async_on_unload = Mock()
    entry.async_create_background_task = Mock()
    hass, entry.runtime_data, added = SimpleNamespace(data={}), runtime, []
    await sensor.async_setup_entry(hass, entry, added.append)
    await binary.async_setup_entry(hass, entry, added.append)
    entry.async_create_background_task.assert_called_once()
    ids = ("bridge-connectivity", "camera-connectivity", "event-archive-problem")
    assert [[e.unique_id for e in batch] for batch in added] == [
        [f"ezviz-01J9ENTRY-{i}" for i in ids]
    ]
    coordinator.data = media.EzvizMediaStatus(None, EzvizStorage("ok", None))
    for listener in listeners:
        listener()
    assert [item.unique_id for item in added[-2] + added[-1]] == [
        "ezviz-01J9ENTRY-microsd",
        "ezviz-01J9ENTRY-microsd-problem",
    ]
