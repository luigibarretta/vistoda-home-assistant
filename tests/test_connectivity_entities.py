"""Device connectivity entities and the native EZVIZ dependency repair."""

from types import SimpleNamespace

import pytest
from ha_stub_support import config_entry, load, stub_ha
from native_ezviz_support import NativeEntry, NativeEzviz

from custom_components.media_bridge import outage

LOADED = SimpleNamespace(value="loaded")
RETRY = SimpleNamespace(value="setup_retry")


def ezviz_entry(entry_id="ez-1", delegate=False):
    entry = config_entry("ezviz", entry_id, ezviz_source_id="SERIAL1:1")
    entry.options = {"ezviz_delegate_controls": True} if delegate else {}
    return entry


def hass_with(native=None, vistoda_entries=(), running=True):
    by_domain = {"media_bridge": list(vistoda_entries)}
    hass = SimpleNamespace(
        is_running=running,
        config_entries=SimpleNamespace(async_entries=lambda domain: by_domain.get(domain, [])),
    )
    (native or NativeEzviz(entries=[])).install(hass)
    return hass


def native(online=True, *, state=LOADED, serial="SERIAL1", camera=True, entries=1):
    natives = [NativeEntry(f"native-{index}", state) for index in range(entries)]
    return NativeEzviz(entries=natives, serial=serial, online=online, camera=camera)


def test_native_camera_follows_the_official_camera_entity_state(monkeypatch) -> None:
    stub_ha(monkeypatch)
    core = load(monkeypatch, "ezviz_core")
    entry = ezviz_entry()
    assert core.native_camera_online(hass_with(native()), entry) is True
    assert core.native_camera_online(hass_with(native(online=False)), entry) is False
    assert core.native_camera_online(hass_with(native(state=RETRY)), entry) is None
    assert core.native_camera_online(hass_with(native(entries=2)), entry) is None
    assert core.native_camera_online(hass_with(native(serial="OTHER")), entry) is None
    assert core.native_camera_online(hass_with(native(camera=False)), entry) is None
    assert core.native_camera_online(hass_with(), config_entry("ezviz")) is None


async def test_ezviz_camera_connectivity_entity(monkeypatch) -> None:
    stub_ha(monkeypatch)
    load(monkeypatch, "ezviz_core")
    platform = load(monkeypatch, "binary_sensor")
    entry = ezviz_entry(delegate=True)
    entity = platform.EzvizCameraConnectivity(entry)
    assert entity.unique_id == "ezviz-ez-1-camera-connectivity"
    assert entity._attr_translation_key == "ezviz_camera_connectivity"
    assert entity.extra_state_attributes["connectivity_scope"] == "camera"
    entity.hass = hass_with(native(online=False))
    await entity.async_added_to_hass()
    assert entity.available is True and entity.is_on is False
    entity.hass = hass_with()
    await entity.async_update()
    assert entity.available is False


def ring_runtime(online=True, device_id="42", success=True):
    status = SimpleNamespace(online=online, device_id=device_id)
    coordinator = SimpleNamespace(data=status, last_update_success=success)
    return SimpleNamespace(ring_status=coordinator, coordinator=coordinator, panel_url=None)


def test_ring_intercom_connectivity_follows_native_status(monkeypatch) -> None:
    stub_ha(monkeypatch)
    platform = load(monkeypatch, "binary_sensor")
    entry = config_entry(ring_device_id="42")
    entity = platform.RingIntercomConnectivity(ring_runtime(online=False), entry)
    assert entity.unique_id == "ring-entry-1-intercom-connectivity"
    assert entity.device_info["identifiers"] == {("media_bridge", "ring:entry-1")}
    assert entity.available is True and entity.is_on is False
    assert platform.RingIntercomConnectivity(ring_runtime(), entry).is_on is True
    unreachable = platform.RingIntercomConnectivity(ring_runtime(success=False), entry)
    assert unreachable.available is False
    retargeted = platform.RingIntercomConnectivity(ring_runtime(device_id="99"), entry)
    assert retargeted.available is False


async def test_setup_adds_device_connectivity_and_keeps_bridge_ids(monkeypatch) -> None:
    stub_ha(monkeypatch)
    platform = load(monkeypatch, "binary_sensor")
    added = []
    ring = config_entry(ring_device_id="42")
    ezviz = ezviz_entry()
    blink = config_entry("blink", "bl-1")
    hass = SimpleNamespace(data={"media_bridge": {}})
    ring.runtime_data, ezviz.runtime_data = ring_runtime(), ring_runtime()
    ezviz.runtime_data.ring_status = None
    blink.runtime_data = SimpleNamespace(
        coordinator=SimpleNamespace(data=None, last_update_success=True),
        ring_status=None,
        panel_url=None,
    )
    for entry in (ring, ezviz, blink):
        await platform.async_setup_entry(hass, entry, added.append)
    ids = [[entity.unique_id for entity in batch] for batch in added]
    assert ids == [
        ["ring-entry-1-bridge-connectivity", "ring-entry-1-intercom-connectivity"],
        ["ezviz-ez-1-bridge-connectivity", "ezviz-ez-1-camera-connectivity"],
        ["blink-entrance-bridge-connectivity"],
    ]
    assert added[0][0].extra_state_attributes["connectivity_scope"] == "bridge"


@pytest.mark.parametrize(
    ("natives", "vistoda", "running", "expected"),
    [
        (native(), [ezviz_entry(delegate=True)], True, "delete"),
        (
            native(state=SimpleNamespace(value="setup_in_progress")),
            [ezviz_entry(delegate=True)],
            True,
            "delete",
        ),
        (native(state=RETRY), [ezviz_entry(delegate=True)], True, "create"),
        # Loaded but without its camera entity: delegation would be forced off.
        (native(camera=False), [ezviz_entry(delegate=True)], True, "create"),
        (native(entries=2), [ezviz_entry(delegate=True)], True, "create"),
        (None, [ezviz_entry(delegate=True)], True, "create"),
        # Standalone entries (the default) never require the native integration.
        (None, [ezviz_entry()], True, "delete"),
        (None, [ezviz_entry(), ezviz_entry("ez-2", delegate=True)], True, "create"),
        (None, [config_entry("ring")], True, "delete"),
        (None, [ezviz_entry(delegate=True)], False, None),
    ],
)
def test_ezviz_core_issue_tracks_native_integration(
    monkeypatch, natives, vistoda, running, expected
) -> None:
    issues = stub_ha(monkeypatch)
    load(monkeypatch, "repairs")
    core = load(monkeypatch, "ezviz_core")
    clock = [0, 900]
    monkeypatch.setattr(outage, "time", SimpleNamespace(monotonic=lambda: clock.pop(0)))
    hass = hass_with(natives, vistoda, running)
    core.refresh_core_issue(hass)
    # A native entry retrying its login, or briefly missing, is not reported at once.
    issues.async_create_issue.assert_not_called()
    core.refresh_core_issue(hass)
    created = issues.async_create_issue.call_args
    deleted = issues.async_delete_issue.call_args
    if expected is None:
        assert created is None and deleted is None
    elif expected == "create":
        assert created.args[2] == "ezviz_core_unavailable" and deleted is None
        assert created.kwargs["translation_key"] == "ezviz_core_unavailable"
    else:
        assert deleted.args[2] == "ezviz_core_unavailable" and created is None


def test_unloading_last_ezviz_entry_clears_core_issue(monkeypatch) -> None:
    issues = stub_ha(monkeypatch)
    load(monkeypatch, "repairs")
    core = load(monkeypatch, "ezviz_core")
    entries = [ezviz_entry(delegate=True)]
    core.refresh_core_issue(hass_with(None, entries), exclude_entry_id="ez-1")
    assert issues.async_delete_issue.call_args.args[2] == "ezviz_core_unavailable"
