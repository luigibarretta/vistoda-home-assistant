"""Administrator-only, paged network backup inventory and verified downloads."""

from urllib.parse import quote

import voluptuous as vol
from aiohttp import web
from homeassistant.components import websocket_api
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import callback

from .backup_storage import archive_entry, configured_mount, storage_mount, storage_readiness
from .blink_usb_auto_backup import CONF_AUTO_BACKUP
from .const import (
    CONF_ALIAS,
    CONF_PROVIDER,
    CONF_SCENETROVE_DEVICE,
    CONF_SHARED_STORAGE,
    PROVIDER_EZVIZ,
)
from .network_archive import checked_file, inventory
from .provider_recording_lists import async_get_provider_recording_lists
from .runtime import entry_runtime
from .shared_archive import SHARED_PREFIX, delete_shared_clip, shared_clip, shared_inventory


@callback
def async_register(hass):
    websocket_api.async_register_command(hass, ws_inventory)
    websocket_api.async_register_command(hass, ws_delete)
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
        entry = archive_entry(hass, msg["entry_id"])
        mount = configured_mount(entry)
        members = None
        if msg["list_id"]:
            lists = await async_get_provider_recording_lists(hass).async_snapshot(
                f"{entry.data[CONF_PROVIDER]}:{entry.entry_id}"
            )
            members = next(
                (set(item["recording_ids"]) for item in lists if item["list_id"] == msg["list_id"]),
                set(),
            )
        shared = shared_location(entry)
        extra = await hass.async_add_executor_job(shared_inventory, *shared) if shared else ()
        result = await hass.async_add_executor_job(
            inventory, mount, msg["page"], msg["page_size"], msg["camera"], members, extra
        )
        for item in result["items"]:
            item["media_path"] = (
                f"/api/media_bridge/network_archive/{quote(entry.entry_id, safe='')}/media"
                f"?file={quote(item['id'], safe='')}"
            )
        result["readiness"] = await hass.async_add_executor_job(storage_readiness, mount)
        result["automatic"] = {
            "enabled": bool(entry.options.get(CONF_AUTO_BACKUP, False)),
            "last_run": getattr(entry_runtime(entry), "usb_backup_status", None),
        }
        connection.send_result(msg["id"], result)
    except (ValueError, OSError, TypeError):
        connection.send_error(msg["id"], "unavailable", "Network archive is unavailable")


@websocket_api.websocket_command(
    {
        vol.Required("type"): "media_bridge/network_archive/delete",
        vol.Required("entry_id"): str,
        vol.Required("ids"): vol.All([vol.All(str, vol.Length(max=256))], vol.Length(max=100)),
    }
)
@websocket_api.async_response
async def ws_delete(hass, connection, msg):
    """Delete archived copies; shared clips leave SceneTrove too."""
    if not connection.user.is_admin:
        connection.send_error(msg["id"], "unauthorized", "Administrator access required")
        return
    try:
        entry = archive_entry(hass, msg["entry_id"])
    except ValueError:
        connection.send_error(msg["id"], "not_found", "Unknown archive entry")
        return
    mount, shared = configured_mount(entry), shared_location(entry)
    deleted, failed = 0, []
    for item_id in msg["ids"]:
        if await hass.async_add_executor_job(delete_copy, mount, shared, item_id):
            deleted += 1
        else:
            failed.append(item_id)
    connection.send_result(msg["id"], {"deleted": deleted, "failed": failed})


def shared_location(entry) -> tuple | None:
    """(mount, device, alias) of an EZVIZ entry's shared SceneTrove folder, when set."""
    storage = entry.options.get(CONF_SHARED_STORAGE)
    if entry.data.get(CONF_PROVIDER) != PROVIDER_EZVIZ or not storage:
        return None
    alias = entry.data[CONF_ALIAS]
    return storage_mount(storage), entry.options.get(CONF_SCENETROVE_DEVICE) or alias, alias


def delete_copy(mount, shared, item_id: str) -> bool:
    """Delete one verified copy and its sidecar; False when refused or absent."""
    if item_id.startswith(SHARED_PREFIX):
        return bool(shared) and delete_shared_clip(*shared, item_id)
    try:
        target, _item = checked_file(mount, item_id)
    except (ValueError, OSError, TypeError, AttributeError):
        return False
    target.unlink()
    target.with_suffix(target.suffix + ".json").unlink(missing_ok=True)
    return True


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
            entry = archive_entry(hass, entry_id)
            mount = configured_mount(entry)
            relative = request.query.get("file", "")

            shared = shared_location(entry)

            def verify():
                if relative.startswith(SHARED_PREFIX) and shared:
                    return shared_clip(*shared, relative, checksum=True)
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
