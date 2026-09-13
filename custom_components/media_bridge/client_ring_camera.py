"""Native Ring camera inventory and direct WebRTC signaling."""

import re
from dataclasses import asdict

from aiohttp import ClientTimeout

from .errors import CannotConnectError
from .models import parse_audio_session


async def cameras(client):
    """Accept only bounded, typed physical camera identities."""
    data = (await client._json("GET", "/v1/cameras")).get("cameras")
    if not isinstance(data, list) or len(data) > 128:
        raise CannotConnectError
    result = []
    for item in data:
        if not isinstance(item, dict) or not valid_id(item.get("device_id")):
            raise CannotConnectError
        if not isinstance(item.get("name"), str) or len(item["name"]) > 255:
            raise CannotConnectError
        capabilities = item.get("capabilities", {})
        if not isinstance(capabilities, dict) or not isinstance(
            capabilities.get("available"), list
        ):
            raise CannotConnectError
        if any(
            not isinstance(item.get(key), (str, type(None))) for key in ("model", "location_name")
        ):
            raise CannotConnectError
        if "live_video_receive" not in capabilities.get("available", []):
            continue
        result.append(
            {
                key: item.get(key)
                for key in ("device_id", "name", "model", "location_name", "capabilities")
            }
        )
    if len({item["device_id"] for item in result}) != len(result):
        raise CannotConnectError
    return result


def valid_id(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9]{1,20}", value) is not None


async def start(client, device_id, offer, mode, ice_ms):
    if not valid_id(device_id):
        raise CannotConnectError
    data = await client._json(
        "POST",
        f"/v1/cameras/{device_id}/video/sessions",
        timeout=ClientTimeout(total=40, connect=5),
        json={
            "expected_device_id": device_id,
            "offer_sdp": offer,
            "mode": mode,
            "ice_gathering_ms": ice_ms,
        },
    )
    result = asdict(parse_audio_session(data))
    if re.fullmatch(r"[A-Za-z0-9_-]{1,64}", result["session_id"]) is None:
        raise CannotConnectError
    return result


async def stop(client, device_id, session_id):
    if not valid_id(device_id) or re.fullmatch(r"[A-Za-z0-9_-]{1,64}", session_id) is None:
        raise CannotConnectError
    await client._empty(
        "DELETE",
        f"/v1/cameras/{device_id}/video/sessions/{session_id}",
        params={"expected_device_id": device_id, "reason": "user_stop"},
    )
