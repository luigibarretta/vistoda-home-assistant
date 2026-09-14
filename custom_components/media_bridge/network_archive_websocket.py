"""Administrator-only, paged network backup inventory and verified downloads."""

from urllib.parse import quote

import voluptuous as vol
from aiohttp import web
from homeassistant.components import websocket_api
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import callback

from .backup_storage import configured_mount, provider_entry, storage_readiness
from .blink_usb_auto_backup import CONF_AUTO_BACKUP, STATUS_KEY
from .const import DOMAIN
from .network_archive import checked_file, inventory
from .provider_recording_lists import async_get_provider_recording_lists


@callback
def async_register(hass):
    websocket_api.async_register_command(hass, ws_inventory)
    hass.http.register_view(NetworkBackupMedia)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "media_bridge/network_archive/list",
        vol.Required("entry_id"): str,
        vol.Optional("page", default=1): vol.All(int, vol.Range(min=1)),
        vol.Optional("page_size", default=10): vol.In((10, 25, 50, 100)),
        vol.Optional("camera", default=""): vol.All(str, vol.Length(max=64)),
        vol.Optional("list_id", default=""): vol.All(str, vol.Length(max=64)),
    }
)
@websocket_api.async_response
async def ws_inventory(hass, connection, msg):
    if not connection.user.is_admin:
        connection.send_error(msg["id"], "unauthorized", "Administrator access required")
        return
    try:
        entry = provider_entry(hass, "blink", msg["entry_id"])
        mount = configured_mount(entry)
        members = None
        if msg["list_id"]:
            lists = await async_get_provider_recording_lists(hass).async_snapshot(
                f"blink:{entry.entry_id}"
            )
            members = next(
                (set(item["recording_ids"]) for item in lists if item["list_id"] == msg["list_id"]),
                set(),
            )
        result = await hass.async_add_executor_job(
            inventory, mount, msg["page"], msg["page_size"], msg["camera"], members
        )
        for item in result["items"]:
            item["media_path"] = (
                f"/api/media_bridge/network_archive/{quote(entry.entry_id, safe='')}/media"
                f"?file={quote(item['id'], safe='')}"
            )
        result["readiness"] = await hass.async_add_executor_job(storage_readiness, mount)
        result["automatic"] = {
            "enabled": bool(entry.options.get(CONF_AUTO_BACKUP, False)),
            "last_run": hass.data.get(DOMAIN, {}).get(STATUS_KEY, {}).get(entry.entry_id),
        }
        connection.send_result(msg["id"], result)
    except (ValueError, OSError, TypeError):
        connection.send_error(msg["id"], "unavailable", "Network archive is unavailable")


class NetworkBackupMedia(HomeAssistantView):
    url = "/api/media_bridge/network_archive/{entry_id}/media"
    name = "api:media_bridge:network-archive"
    requires_auth = True

    async def get(self, request, entry_id):
        user = request.get("hass_user")
        if user is None or not user.is_admin:
            raise web.HTTPForbidden
        hass = request.app["hass"]
        try:
            entry = provider_entry(hass, "blink", entry_id)
            mount = configured_mount(entry)
            relative = request.query.get("file", "")

            def verify():
                return checked_file(mount, relative, checksum=True)

            target, item = await hass.async_add_executor_job(verify)
        except (ValueError, OSError, TypeError):
            raise web.HTTPNotFound from None
        return web.FileResponse(
            target,
            headers={
                "Content-Type": item["media_type"],
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
            },
        )
