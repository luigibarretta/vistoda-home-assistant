"""Unload keeps listeners alive until entities are gone; removal leaves no repair behind."""

import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, Mock

from ha_stub_support import bind_runtime, config_entry, ha_unload, load, stub_ha

from custom_components.media_bridge import outage
from tests.conftest import PACKAGE

RUNTIME_MODULES = {
    "client": "BridgeClient",
    "coordinator": "BridgeCoordinator",
    "ezviz_account": "EzvizDefenceCoordinator",
    "ezviz_alarm_listener": "EzvizAlarmListener",
    "ezviz_controls": "EzvizControlsCoordinator",
    "ezviz_media": "EzvizMediaCoordinator",
    "local": "BlinkAdapterCoordinator",
    "ring_event_listener": "RingEventListener",
    "ring_history": "RingHistoryManager",
    "ring_status": "RingStatusCoordinator",
}


def integration(monkeypatch):
    """Execute the real __init__.py with every runtime dependency replaced."""
    issues = stub_ha(monkeypatch)
    load(monkeypatch, "repairs")

    def module(name, **values):
        result = ModuleType(name)
        result.__dict__.update(values)
        monkeypatch.setitem(sys.modules, name, result)

    module("voluptuous", Schema=Mock(), Optional=lambda key, **_kw: key, ALLOW_EXTRA=1)
    module("homeassistant.helpers.config_validation", string=str)
    module("homeassistant.helpers.aiohttp_client", async_get_clientsession=Mock())
    sys.modules["homeassistant.exceptions"].ConfigEntryNotReady = RuntimeError
    for name, attribute in RUNTIME_MODULES.items():
        # Classes, not mocks: the runtime dataclass annotates `X | None`.
        module(f"custom_components.media_bridge.{name}", **{attribute: type(attribute, (), {})})
    closed = AsyncMock()
    module("custom_components.media_bridge.ring_camera_websocket", async_close_entry=closed)
    module("custom_components.media_bridge.ezviz_core", refresh_core_issue=Mock())
    imported = ModuleType("custom_components.media_bridge.lifecycle_under_test")
    imported.__package__ = "custom_components.media_bridge"
    source = (PACKAGE / "__init__.py").read_text(encoding="utf-8")
    exec(compile(source, str(PACKAGE / "__init__.py"), "exec"), imported.__dict__)
    return SimpleNamespace(module=imported, issues=issues, closed=closed)


def ring_hass(entry, unloaded: bool, order: list[str]):
    async def unload_platforms(_entry, _platforms):
        order.append("platforms")
        return unloaded

    async def stop():
        order.append("listener")

    runtime = SimpleNamespace(ring_events=SimpleNamespace(stop=stop), ezviz_alarms=None)
    bind_runtime(entry, runtime)
    return SimpleNamespace(
        data={"media_bridge": {}},
        config_entries=SimpleNamespace(async_unload_platforms=unload_platforms),
    )


def deleted(env) -> list[str]:
    return [call.args[2] for call in env.issues.async_delete_issue.call_args_list]


async def test_failed_platform_unload_keeps_listeners_and_issues(monkeypatch) -> None:
    env = integration(monkeypatch)
    entry, order = config_entry(), []
    hass = ring_hass(entry, unloaded=False, order=order)
    assert await ha_unload(env.module, hass, entry) is False
    assert order == ["platforms"]
    assert entry.runtime_data.ring_events is not None
    assert deleted(env) == []


async def test_unload_stops_listeners_after_entities_and_clears_issues(monkeypatch) -> None:
    env = integration(monkeypatch)
    entry, order = config_entry(), []
    hass = ring_hass(entry, unloaded=True, order=order)
    outage.outage_clock("bridge_unavailable_entry-1").since = 7
    assert await ha_unload(env.module, hass, entry) is True
    assert order == ["platforms", "listener"]
    assert not hasattr(entry, "runtime_data") and hass.data["media_bridge"] == {}
    env.closed.assert_awaited_once_with(hass, "entry-1")
    assert set(deleted(env)) == {
        "bridge_unavailable_entry-1",
        "ring_push_unavailable_entry-1",
        "ring_push_silent_entry-1",
        "ezviz_binding_unavailable_entry-1",
    }
    # A reload during a lasting outage keeps counting from the original start.
    assert outage.outage_clock("bridge_unavailable_entry-1").since == 7


async def test_removed_entry_leaves_no_issue_or_clock(monkeypatch) -> None:
    env = integration(monkeypatch)
    outage.outage_clock("ezviz_binding_unavailable_entry-1").since = 7
    await env.module.async_remove_entry(SimpleNamespace(), config_entry())
    assert "ezviz_binding_unavailable_entry-1" in deleted(env)
    assert outage.outage_clock("ezviz_binding_unavailable_entry-1").since is None
