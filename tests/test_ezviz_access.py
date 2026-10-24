"""EZVIZ alarm and recording endpoints honour Home Assistant entity permissions."""

import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from aiohttp import web
from ha_stub_support import load

from tests.test_ezviz_alarm_runtime import SOURCE, api_env, batch, request

ENTRY_ID = "01J9ENTRY"
CAMERA = f"ezviz-{ENTRY_ID}-bridge-camera"


def family(readable: set[str]):
    """A non-admin Companion user who may read only `readable` entities."""
    check = Mock(side_effect=lambda entity_id, action: action == "read" and entity_id in readable)
    return SimpleNamespace(
        is_active=True, is_admin=False, permissions=SimpleNamespace(check_entity=check)
    )


def register_camera(entity_id="camera.front_door_live", entry_id=ENTRY_ID, unique_id=CAMERA):
    registry = sys.modules["homeassistant.helpers.entity_registry"].async_get(None)
    registry.entities[entity_id] = SimpleNamespace(
        entity_id=entity_id,
        config_entry_id=entry_id,
        platform="media_bridge",
        unique_id=unique_id,
        disabled_by=None,
    )


def picture_env(monkeypatch):
    client = SimpleNamespace(
        ezviz_camera_identity=AsyncMock(return_value=SOURCE),
        ezviz_alarm_picture=AsyncMock(return_value=b"\xff\xd8\xff" + b"0" * 16),
        ezviz_alarms=AsyncMock(return_value=batch([4], 4)),
    )
    env = api_env(monkeypatch, client)
    register_camera()
    return env, client


@pytest.mark.parametrize(
    ("user", "allowed"),
    [
        (family({"camera.front_door_live"}), True),
        (family({"camera.somewhere_else"}), False),
        (SimpleNamespace(is_active=False, is_admin=True), False),
        (None, False),
    ],
)
async def test_alarm_picture_requires_read_access_to_the_camera(monkeypatch, user, allowed):
    env, client = picture_env(monkeypatch)
    view = env.api.EzvizAlarmPictureView()
    if allowed:
        result = await view.get(request(env.hass, user), ENTRY_ID, "alarm-1")
        assert result.content_type == "image/jpeg"
        return
    with pytest.raises(web.HTTPForbidden):
        await view.get(request(env.hass, user), ENTRY_ID, "alarm-1")
    client.ezviz_alarm_picture.assert_not_called()
    client.ezviz_camera_identity.assert_not_called()


async def test_disabled_or_foreign_camera_entity_grants_nothing(monkeypatch) -> None:
    env, client = picture_env(monkeypatch)
    registry = sys.modules["homeassistant.helpers.entity_registry"].async_get(None)
    registry.entities["camera.front_door_live"].disabled_by = "user"
    register_camera("camera.other_entry", entry_id="OTHER", unique_id="ezviz-OTHER-bridge-camera")
    user = family({"camera.front_door_live", "camera.other_entry"})
    with pytest.raises(web.HTTPForbidden):
        await env.api.EzvizAlarmPictureView().get(request(env.hass, user), ENTRY_ID, "alarm-1")
    client.ezviz_alarm_picture.assert_not_called()


async def test_alarm_history_command_requires_read_access(monkeypatch) -> None:
    env, client = picture_env(monkeypatch)
    denied = SimpleNamespace(user=family(set()), send_result=Mock(), send_error=Mock())
    await env.api.ws_list_alarms(env.hass, denied, {"id": 1, "entry_id": ENTRY_ID})
    assert denied.send_error.call_args.args[1] == "unauthorized"
    client.ezviz_alarms.assert_not_called()
    allowed = SimpleNamespace(
        user=family({"camera.front_door_live"}), send_result=Mock(), send_error=Mock()
    )
    await env.api.ws_list_alarms(env.hass, allowed, {"id": 2, "entry_id": ENTRY_ID})
    assert allowed.send_result.call_args.args[1]["supported"] is True


def recording_proxy(monkeypatch, env):
    module = load(monkeypatch, "provider_recording_proxy")
    # stub_ha makes BridgeRuntime a SimpleNamespace, so this passes its isinstance check.
    runtime = module.BridgeRuntime(client=Mock())
    env.hass.config_entries.async_get_entry(ENTRY_ID).runtime_data = runtime
    return module, runtime


async def test_recording_relay_requires_read_access(monkeypatch) -> None:
    env, _client = picture_env(monkeypatch)
    module, runtime = recording_proxy(monkeypatch, env)
    with pytest.raises(web.HTTPForbidden):
        module._runtime(request(env.hass, family(set())), ENTRY_ID)
    assert module._runtime(request(env.hass, family({"camera.front_door_live"})), ENTRY_ID) is (
        runtime
    )
    admin = SimpleNamespace(is_active=True, is_admin=True)
    assert module._runtime(request(env.hass, admin), ENTRY_ID) is runtime
