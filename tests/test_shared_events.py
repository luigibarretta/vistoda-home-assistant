"""Events in SceneTrove's shared device folder and in the Vistoda archive."""

from types import SimpleNamespace

from release_flow_support import framework
from test_event_archive import DAY, JPEG, alarm


def entry(destination, tmp_path):
    options = {
        "backup_storage": "vistoda_archives",
        "scenetrove_url": "https://st.example",
        "scenetrove_device": "spioncino",
        "clip_destination": destination,
        "shared_storage": "scenetrove_devices",
    }
    return SimpleNamespace(data={"provider": "ezviz", "alias": "front-door"}, options=options)


def modules(monkeypatch):
    """event_archive and the shared_archive bound to it, on a fake network mount."""
    env = framework(monkeypatch)
    env.load("event_folder")
    module = env.load("event_archive")
    monkeypatch.setattr(module.backup_storage, "network_filesystem", lambda path, **_: "nfs")
    return module, env.load("shared_archive")


def folders(monkeypatch, tmp_path, destination):
    module, shared = modules(monkeypatch)
    for mount in ("scenetrove_devices", "vistoda_archives"):
        (tmp_path / mount).mkdir()
    monkeypatch.setattr(shared, "storage_mount", lambda name: tmp_path / name)
    monkeypatch.setattr(shared, "configured_mount", lambda _entry: tmp_path / "vistoda_archives")
    return module, shared.event_folders(entry(destination, tmp_path))


def test_shared_mode_writes_events_under_events_folder(monkeypatch, tmp_path):
    module, (current, _other) = folders(monkeypatch, tmp_path, "shared")
    assert module.write_event(current, alarm("evt-1", DAY), JPEG)
    folder = tmp_path / "scenetrove_devices" / "spioncino" / "_events" / "2026" / "10"
    assert (folder / "20261028T190000Z-evt-1.json").is_file()
    assert (folder / "20261028T190000Z-evt-1.jpg").read_bytes() == JPEG


def test_events_from_both_locations_are_listed_once(monkeypatch, tmp_path):
    module, (vistoda, shared) = folders(monkeypatch, tmp_path, "vistoda")
    for folder in (vistoda, shared):
        module.write_event(folder, alarm("evt-1", DAY), JPEG)
    module.write_event(vistoda, alarm("evt-2", DAY + 60), None)
    page = module.list_events((vistoda, shared), 1, 10)
    assert [item["alarm_id"] for item in page["items"]] == ["evt-2", "evt-1"]
    assert page["pagination"]["total_items"] == 2
    assert module.has_event((shared,), DAY, "evt-1")
    assert module.event_picture((vistoda, shared), "20261028T190000Z-evt-1").is_file()


def test_without_sharing_only_the_vistoda_folder_is_used(monkeypatch, tmp_path):
    _module, shared = modules(monkeypatch)
    monkeypatch.setattr(shared, "configured_mount", lambda _entry: tmp_path / "vistoda_archives")
    plain = SimpleNamespace(data={"provider": "ezviz", "alias": "front-door"}, options={})
    (only,) = shared.event_folders(plain)
    assert only.parts == ("events", "ezviz", "front-door")


def test_deleted_events_are_not_archived_again(monkeypatch, tmp_path):
    module, (shared, vistoda) = folders(monkeypatch, tmp_path, "shared")
    module.write_event(shared, alarm("evt-1", DAY), JPEG)
    assert module.delete_event((shared, vistoda), "20261028T190000Z-evt-1")
    assert module.has_event((shared, vistoda), DAY, "evt-1"), "a backfill must skip it"
    assert module.list_events((shared, vistoda), 1, 10)["items"] == []
    module.prune_events((shared, vistoda), older_than=DAY + 86_400)
    assert module.has_event((shared, vistoda), DAY, "evt-1"), "retention keeps the marker"


def test_another_cameras_shared_events_are_left_alone(monkeypatch, tmp_path):
    module, (shared, _vistoda) = folders(monkeypatch, tmp_path, "shared")
    other = module.shared_folder(shared.mount, "spioncino", "ezviz", "back-door")
    module.write_event(other, alarm("theirs", DAY), JPEG)
    assert not module.delete_event((shared,), "20261028T190000Z-theirs")
    assert module.prune_events((shared,), older_than=DAY + 86_400) == 0
    assert module.has_event((other,), DAY, "theirs")
    assert module.list_events((other,), 1, 10)["pagination"]["total_items"] == 1


def test_event_files_are_readable_by_scenetrove(monkeypatch, tmp_path):
    module, (shared, _vistoda) = folders(monkeypatch, tmp_path, "shared")
    module.write_event(shared, alarm("evt-1", DAY), JPEG)
    folder = tmp_path / "scenetrove_devices" / "spioncino" / "_events" / "2026" / "10"
    assert {oct(path.stat().st_mode & 0o777) for path in folder.iterdir()} == {"0o644"}
