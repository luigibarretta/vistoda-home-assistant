"""Authenticated custom-list commands for Blink and EZVIZ video archives."""

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .const import CONF_PROVIDER, PROVIDER_BLINK, PROVIDER_EZVIZ
from .provider_recording_lists import async_get_provider_recording_lists
from .recording_list_model import RecordingListError

ENTRY_ID = vol.All(str, vol.Length(min=1, max=64))
LIST_ID = vol.All(str, vol.Length(min=1, max=64))
MEDIA_ID = vol.All(
    str,
    vol.Match(r"^(?:local:[0-9a-f-]{36}|usb:\d+:\d+:\d+:\d+)$"),
)
PROVIDER = vol.In((PROVIDER_BLINK, PROVIDER_EZVIZ))


@callback
def async_register(hass: HomeAssistant) -> None:
    for command in (
        ws_list,
        ws_create,
        ws_update,
        ws_delete,
        ws_set_membership,
    ):
        websocket_api.async_register_command(hass, command)


def _scope(hass: HomeAssistant, entry_id: str, provider: str) -> str | None:
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None or entry.data.get(CONF_PROVIDER) != provider:
        return None
    return f"{provider}:{entry_id}"


def _error(connection, message_id: int, error: RecordingListError) -> None:
    labels = {
        "invalid_name": "List name is invalid",
        "duplicate_name": "A list with this name already exists",
        "list_limit": "Recording list limit reached",
        "list_not_found": "Recording list was not found",
        "invalid_recording": "Recording identifier is invalid",
        "membership_limit": "Recording list membership limit reached",
    }
    connection.send_error(message_id, error.code, labels.get(error.code, "Invalid list request"))


def _schema(action: str, extra: dict | None = None) -> dict:
    return {
        vol.Required("type"): f"media_bridge/provider/recording_lists/{action}",
        vol.Required("provider"): PROVIDER,
        vol.Required("entry_id"): ENTRY_ID,
        **(extra or {}),
    }


@websocket_api.websocket_command(_schema("list"))
@websocket_api.async_response
async def ws_list(hass, connection, msg: dict[str, Any]) -> None:
    scope = _scope(hass, msg["entry_id"], msg["provider"])
    if scope is None:
        connection.send_error(msg["id"], "not_found", "Provider entry is not loaded")
        return
    lists = await async_get_provider_recording_lists(hass).async_snapshot(scope)
    connection.send_result(msg["id"], {"lists": lists})


@websocket_api.websocket_command(
    _schema("create", {vol.Required("name"): vol.All(str, vol.Length(min=1, max=64))})
)
@websocket_api.async_response
async def ws_create(hass, connection, msg: dict[str, Any]) -> None:
    scope = _scope(hass, msg["entry_id"], msg["provider"])
    if scope is None:
        connection.send_error(msg["id"], "not_found", "Provider entry is not loaded")
        return
    try:
        lists, list_id = await async_get_provider_recording_lists(hass).async_create(
            scope, msg["name"]
        )
    except RecordingListError as error:
        _error(connection, msg["id"], error)
        return
    connection.send_result(msg["id"], {"lists": lists, "created_list_id": list_id})


@websocket_api.websocket_command(
    _schema(
        "update",
        {
            vol.Required("list_id"): LIST_ID,
            vol.Required("name"): vol.All(str, vol.Length(min=1, max=64)),
        },
    )
)
@websocket_api.async_response
async def ws_update(hass, connection, msg: dict[str, Any]) -> None:
    scope = _scope(hass, msg["entry_id"], msg["provider"])
    if scope is None:
        connection.send_error(msg["id"], "not_found", "Provider entry is not loaded")
        return
    try:
        lists = await async_get_provider_recording_lists(hass).async_update(
            scope, msg["list_id"], msg["name"]
        )
    except RecordingListError as error:
        _error(connection, msg["id"], error)
        return
    connection.send_result(msg["id"], {"lists": lists})


@websocket_api.websocket_command(_schema("delete", {vol.Required("list_id"): LIST_ID}))
@websocket_api.async_response
async def ws_delete(hass, connection, msg: dict[str, Any]) -> None:
    scope = _scope(hass, msg["entry_id"], msg["provider"])
    if scope is None:
        connection.send_error(msg["id"], "not_found", "Provider entry is not loaded")
        return
    lists, deleted = await async_get_provider_recording_lists(hass).async_delete(
        scope, msg["list_id"]
    )
    connection.send_result(msg["id"], {"lists": lists, "deleted": deleted})


@websocket_api.websocket_command(
    _schema(
        "set_membership",
        {
            vol.Required("list_id"): LIST_ID,
            vol.Required("recording_id"): MEDIA_ID,
            vol.Required("included"): bool,
        },
    )
)
@websocket_api.async_response
async def ws_set_membership(hass, connection, msg: dict[str, Any]) -> None:
    scope = _scope(hass, msg["entry_id"], msg["provider"])
    if scope is None:
        connection.send_error(msg["id"], "not_found", "Provider entry is not loaded")
        return
    try:
        lists = await async_get_provider_recording_lists(hass).async_set_membership(
            scope, msg["list_id"], msg["recording_id"], msg["included"]
        )
    except RecordingListError as error:
        _error(connection, msg["id"], error)
        return
    connection.send_result(msg["id"], {"lists": lists})
