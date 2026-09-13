"""Admin-only camera access, separate from delegated Intercom permissions."""

import asyncio
from contextlib import suppress

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import callback

from . import client_ring_camera as camera
from .const import DOMAIN
from .errors import BridgeError, EnrollmentBusyError, RateLimitedError

LEDGER = f"{DOMAIN}_camera_sessions"
DEVICE = vol.All(str, vol.Match(r"^[0-9]{1,20}$"))


@callback
def async_register(hass):
    for handler in (inventory, create, delete):
        websocket_api.async_register_command(hass, handler)


def resolve(hass, entry_id):
    from .websocket import resolve_ring

    result = resolve_ring(hass, entry_id)
    if result is None:
        raise BridgeError("Ring account unavailable")
    return result[0].client


@websocket_api.websocket_command(
    {vol.Required("type"): "media_bridge/ring/cameras", vol.Required("entry_id"): str}
)
@websocket_api.async_response
@websocket_api.require_admin
async def inventory(hass, connection, msg):
    try:
        result = await camera.cameras(resolve(hass, msg["entry_id"]))
    except BridgeError:
        connection.send_error(msg["id"], "unavailable", "Ring camera inventory unavailable")
        return
    connection.send_result(msg["id"], {"cameras": result})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "media_bridge/ring/camera/session/create",
        vol.Required("entry_id"): str,
        vol.Required("camera_id"): DEVICE,
        vol.Required("offer_sdp"): vol.All(str, vol.Length(min=1, max=65536)),
        vol.Required("mode"): vol.In(("listen", "talk")),
        vol.Required("ice_gathering_ms"): vol.All(int, vol.Range(min=0, max=60000)),
    }
)
@websocket_api.async_response
@websocket_api.require_admin
async def create(hass, connection, msg):
    sessions = hass.data.setdefault(LEDGER, {})
    # Reserve before awaiting: concurrent requests cannot bypass the global cap.
    key = (id(connection), msg["id"])
    if len(sessions) >= 8 or any(item["owner"] is connection for item in sessions.values()):
        connection.send_error(msg["id"], "session_busy", "A camera session is already active")
        return
    lease = {
        "owner": connection,
        "entry": msg["entry_id"],
        "camera": msg["camera_id"],
        "request": msg["id"],
    }
    sessions[key] = lease
    connection.subscriptions[msg["id"]] = lambda: sessions.pop(key, None)
    try:
        client = resolve(hass, msg["entry_id"])
        result = await camera.start(
            client, msg["camera_id"], msg["offer_sdp"], msg["mode"], msg["ice_gathering_ms"]
        )
    except BridgeError as error:
        sessions.pop(key, None)
        connection.subscriptions.pop(msg["id"], None)
        code = (
            "cooldown"
            if isinstance(error, RateLimitedError)
            else "session_busy"
            if isinstance(error, EnrollmentBusyError)
            else "unavailable"
        )
        connection.send_error(msg["id"], code, "Ring video session unavailable")
        return
    except BaseException:
        sessions.pop(key, None)
        connection.subscriptions.pop(msg["id"], None)
        raise
    if key not in sessions:
        connection.subscriptions.pop(msg["id"], None)
        with suppress(BridgeError):
            await camera.stop(client, msg["camera_id"], result["session_id"])
        return
    lease["session"] = result["session_id"]

    async def close():
        if sessions.pop(key, None) is None:
            return
        connection.subscriptions.pop(msg["id"], None)
        lease["timer"].cancel()
        with suppress(BridgeError):
            await camera.stop(client, msg["camera_id"], result["session_id"])

    lease["close"] = close

    def cleanup():
        hass.async_create_task(close())

    lease["timer"] = asyncio.get_running_loop().call_later(result["expires_in"], cleanup)
    connection.subscriptions[msg["id"]] = cleanup
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "media_bridge/ring/camera/session/delete",
        vol.Required("entry_id"): str,
        vol.Required("camera_id"): DEVICE,
        vol.Required("session_id"): vol.All(str, vol.Length(min=1, max=64)),
        vol.Optional("reason"): str,
    }
)
@websocket_api.async_response
@websocket_api.require_admin
async def delete(hass, connection, msg):
    leases = list(hass.data.get(LEDGER, {}).values())
    for lease in leases:
        if (
            lease["owner"] is connection
            and lease["entry"] == msg["entry_id"]
            and lease["camera"] == msg["camera_id"]
            and lease.get("session") == msg["session_id"]
        ):
            await lease["close"]()
            break
    connection.send_result(msg["id"], {})


async def async_close_entry(hass, entry_id):
    for key, lease in list(hass.data.get(LEDGER, {}).items()):
        if lease["entry"] == entry_id:
            if "close" in lease:
                await lease["close"]()
            else:
                hass.data[LEDGER].pop(key, None)
                lease["owner"].subscriptions.pop(lease["request"], None)
