"""Authenticated HA boundary for the archived EZVIZ events and their pictures."""

from typing import Any

import voluptuous as vol
from aiohttp import web
from homeassistant.components import websocket_api
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant, callback

from .backup_storage import configured_mount
from .const import CONF_ALIAS, CONF_EVENT_ARCHIVE
from .event_archive import DAY, EVENT_NAME, event_picture, list_events
from .ezviz_alarm_api import PICTURE_CACHE, resolve
from .ring_access import can_access_ezviz_entry

PROVIDER = "ezviz"


def picture_path(entry_id: str, event: str) -> str:
    """Relative, signable path of one archived event picture."""
    return f"/api/media_bridge/events/{entry_id}/{event}.jpg"


class EventPictureView(HomeAssistantView):
    """Serve one archived event picture with the user's HA session."""

    url = "/api/media_bridge/events/{entry_id}/{event}.jpg"
    name = "api:media_bridge:event-picture"
    requires_auth = True

    async def get(self, request: web.Request, entry_id: str, event: str) -> web.FileResponse:
        hass = request.app["hass"]
        if not can_access_ezviz_entry(hass, request.get("hass_user"), entry_id):
            raise web.HTTPForbidden
        resolved = resolve(hass, entry_id) if EVENT_NAME.fullmatch(event) else None
        if resolved is None:
            raise web.HTTPNotFound
        entry, _runtime = resolved
        try:
            path = await hass.async_add_executor_job(
                event_picture, configured_mount(entry), PROVIDER, entry.data[CONF_ALIAS], event
            )
        except (OSError, ValueError) as error:
            raise web.HTTPNotFound from error
        return web.FileResponse(
            path,
            headers={
                "Content-Type": "image/jpeg",
                "Cache-Control": PICTURE_CACHE,
                "X-Content-Type-Options": "nosniff",
            },
        )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "media_bridge/events/list",
        vol.Required("entry_id"): vol.All(str, vol.Length(min=1, max=64)),
        vol.Optional("page", default=1): vol.All(int, vol.Range(min=1)),
        vol.Optional("page_size", default=10): vol.All(int, vol.Range(min=1, max=100)),
        vol.Optional("day", default=""): vol.All(str, vol.Length(max=10)),
    }
)
@websocket_api.async_response
async def ws_list_events(hass, connection, msg: dict[str, Any]) -> None:
    """One page of archived events, newest first; `enabled` false when not opted in."""
    if not can_access_ezviz_entry(hass, connection.user, msg["entry_id"]):
        connection.send_error(msg["id"], "unauthorized", "EZVIZ access is not permitted")
        return
    day = msg.get("day", "")
    if day and not DAY.fullmatch(day):
        connection.send_error(msg["id"], "invalid_format", "day must be YYYY-MM-DD")
        return
    resolved = resolve(hass, msg["entry_id"])
    if resolved is None:
        connection.send_error(msg["id"], "not_found", "EZVIZ bridge is not loaded")
        return
    entry, _runtime = resolved
    if not entry.options.get(CONF_EVENT_ARCHIVE, False):
        connection.send_result(msg["id"], {"enabled": False, "items": [], "pagination": None})
        return
    try:
        page = await hass.async_add_executor_job(
            list_events,
            configured_mount(entry),
            PROVIDER,
            entry.data[CONF_ALIAS],
            msg.get("page", 1),
            msg.get("page_size", 10),
            day,
        )
    except (OSError, ValueError):
        connection.send_error(msg["id"], "unavailable", "The event archive is unavailable")
        return
    items = [
        {**item, "picture": picture_path(entry.entry_id, item["id"]) if item["picture"] else None}
        for item in page["items"]
    ]
    connection.send_result(
        msg["id"], {"enabled": True, "items": items, "pagination": page["pagination"]}
    )


@callback
def async_register(hass: HomeAssistant) -> None:
    """Register the archived event list and picture view once."""
    hass.http.register_view(EventPictureView)
    websocket_api.async_register_command(hass, ws_list_events)
