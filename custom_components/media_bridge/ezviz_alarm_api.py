"""Authenticated HA boundary for EZVIZ alarm history and alarm pictures."""

import re
from typing import Any

import voluptuous as vol
from aiohttp import web
from homeassistant.components import websocket_api
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant, callback

from .client_ezviz_alarms import AlarmsUnsupportedError, alarm_picture_path, valid_picture_id
from .const import CONF_ALIAS, CONF_PROVIDER, DOMAIN, PROVIDER_EZVIZ
from .errors import BridgeError
from .ezviz_binding import async_verify_native

ENTRY_ID = re.compile(r"[A-Za-z0-9]{1,64}")
PICTURE_CACHE = "private, max-age=86400"


def resolve(hass: HomeAssistant, entry_id: str):
    """Return (entry, runtime) for a loaded EZVIZ entry, else None."""
    if not isinstance(entry_id, str) or ENTRY_ID.fullmatch(entry_id) is None:
        return None
    entry = hass.config_entries.async_get_entry(entry_id)
    runtime = hass.data.get(DOMAIN, {}).get(entry_id)
    if (
        entry is None
        or entry.data.get(CONF_PROVIDER) != PROVIDER_EZVIZ
        or getattr(runtime, "client", None) is None
    ):
        return None
    return entry, runtime


class EzvizAlarmPictureView(HomeAssistantView):
    """Relay one alarm picture with the user's HA session (panel and Companion)."""

    url = "/api/media_bridge/ezviz/{entry_id}/alarms/{alarm_id}.jpg"
    name = "api:media_bridge:ezviz-alarm-picture"
    requires_auth = True

    async def get(self, request: web.Request, entry_id: str, alarm_id: str) -> web.Response:
        resolved = resolve(request.app["hass"], entry_id) if valid_picture_id(alarm_id) else None
        if resolved is None:
            raise web.HTTPNotFound
        entry, runtime = resolved
        try:
            await async_verify_native(entry, runtime.client)
            body = await runtime.client.ezviz_alarm_picture(entry.data[CONF_ALIAS], alarm_id)
        except BridgeError as error:
            raise web.HTTPServiceUnavailable from error
        if body is None:
            raise web.HTTPNotFound
        return web.Response(
            body=body,
            content_type="image/jpeg",
            headers={"Cache-Control": PICTURE_CACHE, "X-Content-Type-Options": "nosniff"},
        )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "media_bridge/ezviz/alarms/list",
        vol.Required("entry_id"): vol.All(str, vol.Length(min=1, max=64)),
    }
)
@websocket_api.async_response
async def ws_list_alarms(hass, connection, msg: dict[str, Any]) -> None:
    """Return the app's recent alarm history, newest first, without a cursor."""
    resolved = resolve(hass, msg["entry_id"])
    if resolved is None:
        connection.send_error(msg["id"], "not_found", "EZVIZ bridge is not loaded")
        return
    entry, runtime = resolved
    unsupported = {"supported": False, "alarms": []}
    try:
        await async_verify_native(entry, runtime.client)
        batch = await runtime.client.ezviz_alarms(entry.data[CONF_ALIAS])
    except AlarmsUnsupportedError:
        connection.send_result(msg["id"], unsupported)
        return
    except BridgeError:
        connection.send_error(msg["id"], "unavailable", "EZVIZ alarms are unavailable")
        return
    events = sorted(batch.events, key=lambda item: (item.occurred_at, item.sequence), reverse=True)
    alarms = [
        {
            "alarm_id": alarm.alarm_id,
            "occurred_at": alarm.occurred_at,
            "category": alarm.category,
            "alarm_type": alarm.alarm_type,
            "title": alarm.title,
            "picture": alarm_picture_path(entry.entry_id, alarm),
        }
        for alarm in events[:50]
    ]
    connection.send_result(msg["id"], {"supported": True, "alarms": alarms})


@callback
def async_register(hass: HomeAssistant) -> None:
    """Register the alarm picture relay and history command once."""
    hass.http.register_view(EzvizAlarmPictureView)
    websocket_api.async_register_command(hass, ws_list_alarms)
