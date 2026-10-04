"""Device connectivity entities and the native EZVIZ dependency repair."""

from types import SimpleNamespace

import pytest
from ha_stub_support import config_entry, load, stub_ha

LOADED = SimpleNamespace(value="loaded")
RETRY = SimpleNamespace(value="setup_retry")


def ezviz_entry(entry_id="ez-1"):
    return config_entry("ezviz", entry_id, ezviz_source_id="SERIAL1:1")


def hass_with(native_entries, vistoda_entries=(), running=True):
    by_domain = {"ezviz": list(native_entries), "media_bridge": list(vistoda_entries)}
    return SimpleNamespace(
        is_running=running,
        config_entries=SimpleNamespace(async_entries=lambda domain: by_domain.get(domain, [])),
    )


def native(status, *, success=True, state=LOADED, serial="SERIAL1"):
    coordinator = SimpleNamespace(data={serial: {"status": status}}, last_update_success=success)
    return SimpleNamespace(runtime_data=coordinator, state=state)


@pytest.mark.parametrize(
    ("status", "expected"),
    [(1, True), ("1", True), (2, False), (0, None), (True, None), (None, None), ("x", None)],
)
def test_native_ezviz_status_maps_only_known_codes(monkeypatch, status, expected) -> None:
    stub_ha(monkeypatch)
    core = load(monkeypatch, "ezviz_core")
    assert core.camera_online({"status": status}) is expected


def test_native_camera_requires_one_healthy_coordinator(monkeypatch) -> None:
    stub_ha(monkeypatch)
    core = load(monkeypatch, "ezviz_core")
    entry = ezviz_entry()
    assert core.native_camera_online(hass_with([native(1)]), entry) is True
    assert core.native_camera_online(hass_with([native(2)]), entry) is False
    assert core.native_camera_online(hass_with([native(1, success=False)]), entry) is None
    assert core.native_camera_online(hass_with([native(1), native(1)]), entry) is None
    assert core.native_camera_online(hass_with([native(1, serial="OTHER")]), entry) is None
    assert core.native_camera_online(hass_with([]), config_entry("ezviz")) is None


async def test_ezviz_camera_connectivity_entity(monkeypatch) -> None:
    stub_ha(monkeypatch)
    load(monkeypatch, "ezviz_core")
    platform = load(monkeypatch, "binary_sensor")
    entry = ezviz_entry()
    entity = platform.EzvizCameraConnectivity(entry)
    assert entity.unique_id == "ezviz-ez-1-camera-connectivity"
    assert entity._attr_translation_key == "ezviz_camera_connectivity"
    assert entity.extra_state_attributes["connectivity_scope"] == "camera"
    entity.hass = hass_with([native(2)])
    await entity.async_added_to_hass()
    assert entity.available is True and entity.is_on is False
    entity.hass = hass_with([])
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
    hass = SimpleNamespace(
        data={"media_bridge": {"entry-1": ring_runtime(), "ez-1": ring_runtime(), "bl-1": None}}
    )
    hass.data["media_bridge"]["ez-1"].ring_status = None
    hass.data["media_bridge"]["bl-1"] = SimpleNamespace(
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
        ([native(1)], [ezviz_entry()], True, "delete"),
        (
            [native(1, state=SimpleNamespace(value="setup_in_progress"))],
            [ezviz_entry()],
            True,
            "delete",
        ),
        ([native(1, state=RETRY)], [ezviz_entry()], True, "create"),
        ([], [ezviz_entry()], True, "create"),
        ([], [config_entry("ring")], True, "delete"),
        ([], [ezviz_entry()], False, None),
    ],
)
def test_ezviz_core_issue_tracks_native_integration(
    monkeypatch, natives, vistoda, running, expected
) -> None:
    issues = stub_ha(monkeypatch)
    load(monkeypatch, "repairs")
    core = load(monkeypatch, "ezviz_core")
    core.refresh_core_issue(hass_with(natives, vistoda, running))
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
    core.refresh_core_issue(hass_with([], [ezviz_entry()]), exclude_entry_id="ez-1")
    assert issues.async_delete_issue.call_args.args[2] == "ezviz_core_unavailable"
