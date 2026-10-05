"""EZVIZ controls coordinator, repair suppression, connectivity and account alarm panel."""

import enum
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from ha_stub_support import (
    AuthFailedError,
    Coordinator,
    CoordinatorEntity,
    Entity,
    UpdateFailedError,
    config_entry,
    load,
    stub_ha,
)

from custom_components.media_bridge.client_ezviz_controls import (
    EzvizControlConflictError,
    EzvizControls,
    EzvizControlUnconfirmedError,
)
from custom_components.media_bridge.client_ezviz_media import EzvizFeatureUnsupportedError
from custom_components.media_bridge.errors import CannotConnectError, ReauthRequiredError


class HomeAssistantError(Exception):
    pass


class AlarmState(enum.StrEnum):
    DISARMED = "disarmed"
    ARMED_HOME = "armed_home"
    ARMED_AWAY = "armed_away"


def ezviz_entry(entry_id="E1", url="http://app:8787"):
    return config_entry("ezviz", entry_id, url=url, ezviz_source_id="SERIAL1:1")


def stub(monkeypatch):
    issues = stub_ha(monkeypatch)
    sys.modules["homeassistant.exceptions"].HomeAssistantError = HomeAssistantError
    alarm = ModuleType("homeassistant.components.alarm_control_panel")
    alarm.AlarmControlPanelEntity = Entity
    alarm.AlarmControlPanelEntityFeature = SimpleNamespace(ARM_HOME=1, ARM_AWAY=2)
    alarm.AlarmControlPanelState = AlarmState
    monkeypatch.setitem(sys.modules, alarm.__name__, alarm)
    load(monkeypatch, "repairs")
    load(monkeypatch, "ezviz_core")
    return issues, load(monkeypatch, "ezviz_controls")


def hass_with(entries, runtimes=None, natives=()):
    by_domain = {"media_bridge": list(entries), "ezviz": list(natives)}
    return SimpleNamespace(
        is_running=True,
        data={"media_bridge": runtimes or {}},
        config_entries=SimpleNamespace(async_entries=lambda domain: by_domain.get(domain, [])),
    )


async def test_coordinator_detects_support_404_and_skips_unhealthy_bridge(monkeypatch) -> None:
    _issues, controls = stub(monkeypatch)
    bridge = SimpleNamespace(last_update_success=True)
    client = SimpleNamespace(ezviz_controls=AsyncMock(return_value=EzvizControls(online=True)))
    coordinator = controls.EzvizControlsCoordinator(hass_with([]), ezviz_entry(), client, bridge)
    status = await coordinator._async_update_data()
    assert controls.supports_controls(status) and status.controls.online is True
    assert controls.CONTROLS_INTERVAL.total_seconds() == 60
    client.ezviz_controls.side_effect = [EzvizFeatureUnsupportedError()]
    assert await coordinator._async_update_data() == controls.UNSUPPORTED
    for error, expected in ((ReauthRequiredError(), AuthFailedError), (CannotConnectError(), None)):
        client.ezviz_controls.side_effect = [error]
        with pytest.raises(expected or UpdateFailedError):
            await coordinator._async_update_data()
    bridge.last_update_success = False
    client.ezviz_controls.reset_mock()
    with pytest.raises(UpdateFailedError):
        await coordinator._async_update_data()
    client.ezviz_controls.assert_not_called()


@pytest.mark.parametrize(
    ("status", "expected"),
    [("supported", "delete"), ("unsupported", "create"), ("unknown", "create")],
)
def test_core_repair_is_suppressed_once_the_app_supports_controls(
    monkeypatch, status, expected
) -> None:
    issues, controls = stub(monkeypatch)
    data = {
        "supported": controls.EzvizControlsStatus(True, EzvizControls()),
        "unsupported": controls.UNSUPPORTED,
        "unknown": None,
    }[status]
    runtime = SimpleNamespace(ezviz_controls=SimpleNamespace(data=data))
    core = sys.modules["custom_components.media_bridge.ezviz_core"]
    core.refresh_core_issue(hass_with([ezviz_entry()], {"E1": runtime}))
    call = issues.async_delete_issue if expected == "delete" else issues.async_create_issue
    assert call.call_args.args[2] == "ezviz_core_unavailable"


async def test_connectivity_prefers_app_online_and_falls_back_to_native(monkeypatch) -> None:
    _issues, controls = stub(monkeypatch)
    platform = load(monkeypatch, "binary_sensor")
    coordinator = SimpleNamespace(
        data=controls.EzvizControlsStatus(True, EzvizControls(online=False)),
        last_update_success=True,
    )
    native = SimpleNamespace(
        runtime_data=SimpleNamespace(data={"SERIAL1": {"status": 1}}, last_update_success=True),
        state=SimpleNamespace(value="loaded"),
    )
    entity = platform.EzvizCameraConnectivity(ezviz_entry())
    entity.hass = hass_with([], {"E1": SimpleNamespace(ezviz_controls=coordinator)}, [native])
    await entity.async_update()
    assert (entity.available, entity.is_on) == (True, False)
    assert entity.extra_state_attributes["source_integration"] == "media_bridge"
    coordinator.data = controls.UNSUPPORTED
    await entity.async_update()
    assert entity.is_on is True
    assert entity.extra_state_attributes["source_integration"] == "ezviz"


def alarm_env(monkeypatch, mode="home"):
    stub(monkeypatch)
    sys.modules["homeassistant.helpers.update_coordinator"].CoordinatorEntity = CoordinatorEntity
    account = load(monkeypatch, "ezviz_account")
    load(monkeypatch, "entity_gate")
    platform = load(monkeypatch, "alarm_control_panel")
    client = SimpleNamespace(
        ezviz_account_defence=AsyncMock(return_value=mode),
        ezviz_set_account_defence=AsyncMock(),
    )
    coordinator = account.EzvizDefenceCoordinator(
        None, ezviz_entry(), client, SimpleNamespace(last_update_success=True)
    )
    coordinator.data = account.EzvizDefenceStatus(True, mode)

    async def refresh():
        coordinator.data = await coordinator._async_update_data()

    coordinator.async_refresh = refresh
    coordinator.async_set_updated_data = lambda data: setattr(coordinator, "data", data)
    return account, platform, coordinator, client


async def test_alarm_panel_maps_modes_like_home_assistant_core(monkeypatch) -> None:
    account, platform, coordinator, client = alarm_env(monkeypatch)
    entity = platform.EzvizAccountAlarm(coordinator, "E1")
    assert entity.unique_id == "ezviz-E1-account-defence"
    assert entity.device_info["identifiers"] == {("media_bridge", "ezviz-account:E1")}
    assert entity.available and entity.alarm_state == "disarmed"
    for service, mode, state in (
        (entity.async_alarm_arm_away, "away", "armed_away"),
        (entity.async_alarm_arm_home, "sleep", "armed_home"),
        (entity.async_alarm_disarm, "home", "disarmed"),
    ):
        previous = coordinator.data.mode
        client.ezviz_set_account_defence.return_value = mode
        await service()
        assert client.ezviz_set_account_defence.await_args.args == (mode, previous)
        assert entity.alarm_state == state
    coordinator.data = account.EzvizDefenceStatus(True, None)
    assert entity.alarm_state is None
    coordinator.data = account.EzvizDefenceStatus(False)
    assert not entity.available


async def test_alarm_panel_rejects_conflicts_and_unconfirmed_modes(monkeypatch) -> None:
    _account, platform, coordinator, client = alarm_env(monkeypatch, mode="home")
    entity = platform.EzvizAccountAlarm(coordinator, "E1")
    client.ezviz_set_account_defence.side_effect = [
        EzvizControlConflictError(),
        EzvizControlUnconfirmedError(),
        CannotConnectError(),
    ]
    client.ezviz_account_defence.return_value = "sleep"
    for _ in range(3):
        with pytest.raises(HomeAssistantError):
            await entity.async_alarm_arm_away()
    assert entity.alarm_state == "armed_home"  # Refreshed, never the requested mode.
    client.ezviz_set_account_defence.side_effect = None
    client.ezviz_set_account_defence.return_value = None
    client.ezviz_account_defence.return_value = "home"
    with pytest.raises(HomeAssistantError):
        await entity.async_alarm_arm_away()


async def test_only_the_app_owner_entry_creates_one_alarm_panel(monkeypatch) -> None:
    account, platform, _coordinator, _client = alarm_env(monkeypatch)
    monkeypatch.setattr(Coordinator, "async_add_listener", lambda _self, _l: Mock(), raising=False)
    monkeypatch.setattr(Coordinator, "async_refresh", Mock(), raising=False)
    first, second = ezviz_entry("A1"), ezviz_entry("B2")
    other_app = ezviz_entry("A0", url="http://other:8787")
    disabled = ezviz_entry("A")
    disabled.disabled_by = "user"
    hass = hass_with([second, first, other_app, disabled])
    assert account.account_owner_id(hass, second) == "A1"
    assert account.account_owner_id(hass, other_app) == "A0"
    for entry in (first, second):
        entry.async_on_unload = Mock()
        entry.async_create_background_task = Mock()
        runtime = SimpleNamespace(client=SimpleNamespace(), coordinator=SimpleNamespace())
        hass.data["media_bridge"][entry.entry_id] = runtime
        await platform.async_setup_entry(hass, entry, Mock())
    assert hass.data["media_bridge"]["A1"].ezviz_defence is not None
    assert not hasattr(hass.data["media_bridge"]["B2"], "ezviz_defence")
    first.async_create_background_task.assert_called_once()
    second.async_create_background_task.assert_not_called()


def test_panel_metadata_prefers_vistoda_alarm_and_battery(monkeypatch) -> None:
    _issues, controls = stub(monkeypatch)
    account = load(monkeypatch, "ezviz_account")
    native = ModuleType("custom_components.media_bridge.ezviz_panel_metadata")
    native.panel_metadata = lambda _hass, _entry: {"alarm_entity_id": "alarm_control_panel.n"}
    monkeypatch.setitem(sys.modules, native.__name__, native)
    ids = {
        ("alarm_control_panel", "ezviz-E1-account-defence"): "alarm_control_panel.vistoda",
        ("sensor", "ezviz-E1-battery"): "sensor.vistoda_battery",
    }
    registry = SimpleNamespace(async_get_entity_id=lambda d, _p, key: ids.get((d, key)))
    sys.modules["homeassistant.helpers.entity_registry"].async_get = lambda _hass: registry
    module = load(monkeypatch, "panel_entry_metadata")
    data = controls.EzvizControlsStatus(True, EzvizControls(ptz=True, battery_percent=55))
    runtime = SimpleNamespace(
        ezviz_controls=SimpleNamespace(data=data),
        ezviz_defence=SimpleNamespace(data=account.EzvizDefenceStatus(True, "away")),
    )
    hass = hass_with([ezviz_entry()], {"E1": runtime})
    result = module.entry_metadata(hass, ezviz_entry(), "ezviz")
    assert result["controls"] == {
        "supported": True,
        "ptz": True,
        "online": None,
        "battery_percent": 55,
    }
    assert result["alarm_entity_id"] == "alarm_control_panel.vistoda"
    assert result["battery_entity_id"] == "sensor.vistoda_battery"
    runtime.ezviz_controls.data = controls.UNSUPPORTED
    result = module.entry_metadata(hass, ezviz_entry(), "ezviz")
    assert result["alarm_entity_id"] == "alarm_control_panel.n"
    assert result["controls"]["supported"] is False and "battery_entity_id" not in result
