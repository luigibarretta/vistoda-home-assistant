"""EZVIZ alarm history websocket: newest page, older pages and resets."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from custom_components.media_bridge.client_ezviz_alarms import AlarmsUnsupportedError
from custom_components.media_bridge.errors import CannotConnectError
from tests.test_ezviz_alarm_runtime import ADMIN, SOURCE, api_env, batch


async def test_history_command_reports_old_apps_without_errors(monkeypatch) -> None:
    client = SimpleNamespace(
        ezviz_camera_identity=AsyncMock(return_value=SOURCE),
        ezviz_alarms=AsyncMock(side_effect=[batch([4, 5], 5), AlarmsUnsupportedError()]),
    )
    env = api_env(monkeypatch, client)
    connection = SimpleNamespace(user=ADMIN, send_result=Mock(), send_error=Mock())
    await env.api.ws_list_alarms(env.hass, connection, {"id": 1, "entry_id": "01J9ENTRY"})
    result = connection.send_result.call_args.args[1]
    assert result["supported"] is True
    assert [alarm["alarm_id"] for alarm in result["alarms"]] == ["alarm-5", "alarm-4"]
    assert result["alarms"][0]["picture"] == "/api/media_bridge/ezviz/01J9ENTRY/alarms/alarm-5.jpg"
    client.ezviz_alarms.assert_awaited_with("front-door")
    await env.api.ws_list_alarms(env.hass, connection, {"id": 2, "entry_id": "01J9ENTRY"})
    assert connection.send_result.call_args.args[1] == {"supported": False, "alarms": []}
    client.ezviz_alarms.side_effect = [CannotConnectError()]
    await env.api.ws_list_alarms(env.hass, connection, {"id": 3, "entry_id": "01J9ENTRY"})
    assert connection.send_error.call_args.args[1] == "unavailable"
    await env.api.ws_list_alarms(env.hass, connection, {"id": 4, "entry_id": "missing"})
    assert connection.send_error.call_args.args[1] == "not_found"


async def test_history_command_pages_back_and_resets_on_a_new_generation(monkeypatch) -> None:
    client = SimpleNamespace(
        ezviz_camera_identity=AsyncMock(return_value=SOURCE),
        ezviz_alarms=AsyncMock(
            side_effect=[
                batch([4, 5], 5, older=4),
                batch([2, 3], 5, older=2),
                batch([1], 3, "gen-b"),
                batch([2, 3], 3, "gen-b"),
            ]
        ),
    )
    env = api_env(monkeypatch, client)
    connection = SimpleNamespace(user=ADMIN, send_result=Mock(), send_error=Mock())
    await env.api.ws_list_alarms(env.hass, connection, {"id": 1, "entry_id": "01J9ENTRY"})
    first = connection.send_result.call_args.args[1]
    assert (first["generation"], first["older"], first["reset"]) == ("gen-a", 4, False)
    message = {"id": 2, "entry_id": "01J9ENTRY", "before": 4, "generation": "gen-a"}
    await env.api.ws_list_alarms(env.hass, connection, message)
    page = connection.send_result.call_args.args[1]
    assert [alarm["alarm_id"] for alarm in page["alarms"]] == ["alarm-3", "alarm-2"]
    assert (page["older"], page["reset"]) == (2, False)
    client.ezviz_alarms.assert_awaited_with("front-door", before=4)
    message = {"id": 3, "entry_id": "01J9ENTRY", "before": 2, "generation": "gen-a"}
    await env.api.ws_list_alarms(env.hass, connection, message)
    reset = connection.send_result.call_args.args[1]
    assert reset["reset"] is True, "a restarted app reassigned the sequences"
    assert [alarm["alarm_id"] for alarm in reset["alarms"]] == ["alarm-3", "alarm-2"]
    assert (reset["generation"], reset["older"]) == ("gen-b", None)
    client.ezviz_alarms.assert_awaited_with("front-door")
    calls = client.ezviz_alarms.await_count
    for message in (
        {"id": 4, "entry_id": "01J9ENTRY", "before": 2},
        {"id": 5, "entry_id": "01J9ENTRY", "generation": "gen-b"},
    ):
        await env.api.ws_list_alarms(env.hass, connection, message)
        assert connection.send_error.call_args.args[1] == "invalid_format"
    assert client.ezviz_alarms.await_count == calls
