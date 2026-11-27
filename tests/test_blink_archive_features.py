"""The panel switches for Blink USB, HA-local recordings and network backup, and what follows."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from release_flow_support import framework
from test_blink_auto_backup import worker_fixture, ws_fixture


def update_entry(env):
    def update(entry, options):
        entry.options = options

    env.hass.config_entries.async_update_entry = Mock(side_effect=update)


async def call_set(module, env, connection, entry, **flags):
    message = {"id": 1, "entry_id": entry.entry_id, **flags}
    await module.ws_set_archive_features(env.hass, connection, message)


async def test_every_archive_is_on_until_the_user_turns_it_off(monkeypatch):
    env, module, entry, connection = ws_fixture(monkeypatch)
    await module.ws_recording_options(env.hass, connection, {"id": 1, "entry_id": entry.entry_id})
    result = connection.send_result.call_args.args[1]
    assert (result["usb"], result["local_ha"], result["nfs"]) == (True, True, True)
    entry.options["blink_use_local_ha"] = False
    await module.ws_recording_options(env.hass, connection, {"id": 2, "entry_id": entry.entry_id})
    assert connection.send_result.call_args.args[1]["local_ha"] is False


async def test_only_administrators_change_the_archives(monkeypatch):
    env, module, entry, connection = ws_fixture(monkeypatch, admin=False)
    update_entry(env)
    await call_set(module, env, connection, entry, usb=False)
    assert connection.send_error.call_args.args[1] == "unauthorized"
    env.hass.config_entries.async_update_entry.assert_not_called()


async def test_turning_the_network_backup_off_turns_the_automatic_backup_off(monkeypatch):
    env, module, entry, connection = ws_fixture(monkeypatch)
    update_entry(env)
    entry.options["blink_usb_auto_backup"] = True
    await call_set(module, env, connection, entry, nfs=False)
    assert entry.options["blink_use_nfs"] is False
    assert entry.options["blink_usb_auto_backup"] is False
    # And it cannot be switched back on while the network backup is off.
    await module.ws_set_auto_backup(
        env.hass, connection, {"id": 2, "entry_id": entry.entry_id, "enabled": True}
    )
    assert connection.send_error.call_args.args[1:] == ("storage_unavailable", "nfs_disabled")


async def test_turning_ha_local_off_stops_motion_recording_once(monkeypatch):
    env, module, entry, connection = ws_fixture(monkeypatch)
    update_entry(env)
    current = {"enabled": True, "duration_seconds": 30, "cameras": ["front"]}
    client = SimpleNamespace(get_json=AsyncMock(return_value=current), put_json=AsyncMock())
    env.hass.data = {"blink_live_bridge": {"runtime": SimpleNamespace(client=client)}}
    await call_set(module, env, connection, entry, local_ha=False)
    client.put_json.assert_awaited_once_with("/v1/motion/recording", {**current, "enabled": False})
    await call_set(module, env, connection, entry, local_ha=False)  # Already off: left alone.
    assert client.put_json.await_count == 1
    # A failing provider never blocks the switch.
    client.put_json.side_effect = RuntimeError("provider down")
    await call_set(module, env, connection, entry, local_ha=True)
    await call_set(module, env, connection, entry, local_ha=False)
    assert entry.options["blink_use_local_ha"] is False


async def test_the_background_worker_follows_the_switches(monkeypatch, tmp_path):
    _env, local, worker, _client = worker_fixture(monkeypatch, tmp_path, {})
    assert worker.enabled()
    worker.entry.options["blink_use_nfs"] = False
    assert not worker.enabled()
    worker.entry.options["blink_use_nfs"] = True
    worker.usb_pass = AsyncMock(return_value=("complete", 0, 0))
    copy = AsyncMock(side_effect=AssertionError("HA-local recordings are switched off"))
    monkeypatch.setattr(local, "local_pass", copy)
    worker.entry.options["blink_use_local_ha"] = False
    result = await worker.run()
    assert result["status"] == "complete" and result["local_checked"] == 0
    copy.assert_not_awaited()


async def test_manual_backup_is_refused_while_the_network_backup_is_off(monkeypatch):
    env = framework(monkeypatch)
    backup = env.load("recording_backup")
    configured = ws_fixture(monkeypatch)[2]
    env.entries[configured.entry_id] = configured
    configured.options["blink_use_nfs"] = False
    source = AsyncMock()
    monkeypatch.setattr(backup, "_source", source)
    connection = SimpleNamespace(
        user=SimpleNamespace(is_admin=True), send_error=Mock(), send_result=Mock()
    )
    message = {
        "id": 1,
        "provider": "blink",
        "entry_id": configured.entry_id,
        "recording_id": "00000000-0000-4000-8000-000000000001",
    }
    await backup.ws_backup_recording(env.hass, connection, message)
    assert connection.send_error.call_args.args[1] == "unavailable"
    source.assert_not_awaited()  # Refused before reading any media.
