"""EZVIZ delegation switch, forced-off policy at setup, repair scope and alarm ownership."""

import enum
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from ha_stub_support import CoordinatorEntity, Entity, config_entry, load, stub_ha

URL = "http://app:8787"


class HomeAssistantError(Exception):
    pass


class ServiceValidationError(HomeAssistantError):
    pass


class State(enum.Enum):
    LOADED = "loaded"
    NOT_LOADED = "not_loaded"


def stub(monkeypatch):
    issues = stub_ha(monkeypatch)
    exceptions = sys.modules["homeassistant.exceptions"]
    exceptions.HomeAssistantError = HomeAssistantError
    exceptions.ServiceValidationError = ServiceValidationError
    sys.modules["homeassistant.helpers.entity"].EntityCategory = SimpleNamespace(CONFIG="config")
    sys.modules["homeassistant.config_entries"].ConfigEntryState = State
    started = []
    values = {
        "homeassistant.components.switch": {"SwitchEntity": Entity},
        "homeassistant.helpers.start": {
            "async_at_started": lambda _hass, job: started.append(job) or Mock()
        },
        "homeassistant.components.alarm_control_panel": {
            "AlarmControlPanelEntity": Entity,
            "AlarmControlPanelEntityFeature": SimpleNamespace(ARM_HOME=1, ARM_AWAY=2),
            "AlarmControlPanelState": str,
        },
    }
    for name, attributes in values.items():
        module = ModuleType(name)
        module.__dict__.update(attributes)
        monkeypatch.setitem(sys.modules, name, module)
    sys.modules["homeassistant.helpers.update_coordinator"].CoordinatorEntity = CoordinatorEntity
    load(monkeypatch, "repairs")
    load(monkeypatch, "ezviz_core")
    return issues, started, load(monkeypatch, "ezviz_policy")


def ezviz_entry(entry_id="E1", *, delegate=False, state=State.LOADED):
    entry = config_entry("ezviz", entry_id, url=URL, ezviz_source_id="SERIAL1:1")
    entry.options = {"ezviz_delegate_controls": delegate}
    entry.state = state
    entry.async_on_unload = Mock()
    return entry


def hass_with(entries, *, native=True, running=True):
    coordinator = SimpleNamespace(data={"SERIAL1": {"status": 1}}, last_update_success=True)
    natives = [SimpleNamespace(runtime_data=coordinator, state=SimpleNamespace(value="loaded"))]
    by_domain = {"media_bridge": list(entries), "ezviz": natives if native else []}

    def update(entry, options):
        entry.options = options

    return SimpleNamespace(
        is_running=running,
        data={"media_bridge": {}},
        auth=SimpleNamespace(async_get_user=AsyncMock()),
        config_entries=SimpleNamespace(
            async_entries=lambda domain: by_domain.get(domain, []),
            async_update_entry=Mock(side_effect=update),
            async_schedule_reload=Mock(),
        ),
    )


def reloaded(hass) -> list[str]:
    return [call.args[0] for call in hass.config_entries.async_schedule_reload.call_args_list]


def test_option_is_forced_off_at_setup_when_native_is_unavailable(monkeypatch) -> None:
    issues, _started, policy = stub(monkeypatch)
    entry, sibling = ezviz_entry(delegate=True), ezviz_entry("E2")
    other_app = ezviz_entry("E3")
    other_app.data["url"] = "http://other:8787"
    hass = hass_with([entry, sibling, other_app], native=False)
    policy.enforce_delegate_policy(hass, entry)
    assert entry.options["ezviz_delegate_controls"] is False
    # The entry being set up reads the corrected option; only its app siblings reload.
    assert reloaded(hass) == ["E2"]
    # No delegated entry is left, so no repair is raised.
    assert issues.async_delete_issue.call_args.args[2] == "ezviz_core_unavailable"
    issues.async_create_issue.assert_not_called()


def test_option_is_kept_when_native_is_available_or_already_standalone(monkeypatch) -> None:
    _issues, started, policy = stub(monkeypatch)
    delegated = ezviz_entry(delegate=True)
    hass = hass_with([delegated])
    policy.enforce_delegate_policy(hass, delegated)
    assert delegated.options["ezviz_delegate_controls"] is True
    standalone = ezviz_entry("E2")
    policy.enforce_delegate_policy(hass_with([standalone], native=False), standalone)
    assert standalone.options["ezviz_delegate_controls"] is False
    hass.config_entries.async_update_entry.assert_not_called()
    assert started == []


def test_startup_defers_the_decision_until_home_assistant_started(monkeypatch) -> None:
    _issues, started, policy = stub(monkeypatch)
    entry = ezviz_entry(delegate=True)
    hass = hass_with([entry], native=False, running=False)
    policy.enforce_delegate_policy(hass, entry)
    assert entry.options["ezviz_delegate_controls"] is True  # Native may still be loading.
    entry.async_on_unload.assert_called_once()
    hass.is_running = True
    started[0](hass)
    assert entry.options["ezviz_delegate_controls"] is False
    assert reloaded(hass) == ["E1"]  # Already set up as delegated: reload itself.


async def test_switch_mirrors_ring_and_reloads_the_app_entries(monkeypatch) -> None:
    issues, _started, policy = stub(monkeypatch)
    entry, sibling = ezviz_entry(), ezviz_entry("E2")
    hass = hass_with([entry, sibling, ezviz_entry("E3", state=State.NOT_LOADED)])
    switch = policy.EzvizDelegateSwitch(hass, entry)
    switch._context = SimpleNamespace(user_id=None)
    switch.async_write_ha_state = Mock()
    assert switch.unique_id == "ezviz-E1-delegate-controls"
    assert switch._attr_translation_key == "ezviz_delegate_controls"
    assert switch._attr_entity_category == "config"
    assert switch._attr_icon == "mdi:swap-horizontal"
    assert switch.is_on is False and switch.available is True
    assert switch.extra_state_attributes["control_source"] == "vistoda"
    await switch.async_turn_on()
    assert entry.options["ezviz_delegate_controls"] is True
    assert reloaded(hass) == ["E1", "E2"]
    assert switch.extra_state_attributes["control_source"] == "official_ezviz"
    issues.async_delete_issue.assert_called()  # Native is loaded: no repair.
    await switch.async_turn_off()
    assert entry.options["ezviz_delegate_controls"] is False


async def test_switch_is_unavailable_and_refuses_on_without_native(monkeypatch) -> None:
    _issues, _started, policy = stub(monkeypatch)
    entry = ezviz_entry()
    hass = hass_with([entry], native=False)
    switch = policy.EzvizDelegateSwitch(hass, entry)
    switch._context = SimpleNamespace(user_id=None)
    switch.async_write_ha_state = Mock()
    assert switch.available is False
    with pytest.raises(HomeAssistantError):
        await switch.async_turn_on()
    assert entry.options["ezviz_delegate_controls"] is False
    # A delegated entry whose native integration vanished can still be turned off.
    entry.options = {"ezviz_delegate_controls": True}
    assert switch.available is True
    await switch.async_turn_off()
    assert entry.options["ezviz_delegate_controls"] is False


async def test_switch_requires_an_administrator(monkeypatch) -> None:
    _issues, _started, policy = stub(monkeypatch)
    entry = ezviz_entry()
    hass = hass_with([entry])
    hass.auth.async_get_user.return_value = SimpleNamespace(is_active=True, is_admin=False)
    switch = policy.EzvizDelegateSwitch(hass, entry)
    switch._context = SimpleNamespace(user_id="user-1")
    with pytest.raises(ServiceValidationError):
        await switch.async_turn_on()
    hass.config_entries.async_update_entry.assert_not_called()


async def test_alarm_panel_exists_only_in_standalone_mode(monkeypatch) -> None:
    stub(monkeypatch)
    account = load(monkeypatch, "ezviz_account")
    load(monkeypatch, "entity_gate")
    platform = load(monkeypatch, "alarm_control_panel")
    delegated, standalone = ezviz_entry("A1", delegate=True), ezviz_entry("B2")
    hass = hass_with([delegated, standalone])
    # The delegated entry relies on the official panel; the standalone one owns Vistoda's.
    assert account.account_owner_id(hass, delegated) == "B2"
    removed = []
    registry = SimpleNamespace(
        async_get_entity_id=lambda _d, _p, unique_id: f"alarm_control_panel.{unique_id}",
        async_remove=removed.append,
        async_get_device=lambda identifiers: None,
    )
    sys.modules["homeassistant.helpers.entity_registry"].async_get = lambda _hass: registry
    sys.modules["homeassistant.helpers.device_registry"].async_get = lambda _hass: registry
    add = Mock()
    runtime = SimpleNamespace(client=SimpleNamespace(), coordinator=SimpleNamespace())
    hass.data["media_bridge"]["A1"] = runtime
    delegated.async_create_background_task = Mock()
    await platform.async_setup_entry(hass, delegated, add)
    add.assert_not_called()
    assert not hasattr(runtime, "ezviz_defence")
    # A panel left from standalone mode is removed instead of lingering as a duplicate.
    assert removed == ["alarm_control_panel.ezviz-A1-account-defence"]
    for entry in (delegated, standalone):
        entry.options = {"ezviz_delegate_controls": True}
    assert account.account_owner_id(hass, standalone) is None
