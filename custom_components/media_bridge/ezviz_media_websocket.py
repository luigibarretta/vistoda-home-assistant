"""Authenticated, read-only microSD record timeline for one EZVIZ camera."""

import re
from datetime import date, timedelta
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.util import dt as dt_util

from .client_ezviz_media import EzvizFeatureUnsupportedError
from .const import CONF_ALIAS
from .errors import BridgeError
from .ezviz_alarm_api import resolve
from .ezviz_binding import async_verify_native

DAY = re.compile(r"\d{4}-\d{2}-\d{2}")
# The panel offers the last seven days; one extra day on each side absorbs a
# browser whose time zone differs from Home Assistant's.
HISTORY_DAYS = 7


def requested_day(value, today: date) -> date | None:
    """Accept only an ISO calendar day inside the bounded history window."""
    if not isinstance(value, str) or DAY.fullmatch(value) is None:
        return None
    try:
        day = date.fromisoformat(value)
    except ValueError:
        return None
    if not today - timedelta(days=HISTORY_DAYS) <= day <= today + timedelta(days=1):
        return None
    return day


@websocket_api.websocket_command(
    {
        vol.Required("type"): "media_bridge/ezviz/sd_records/list",
        vol.Required("entry_id"): vol.All(str, vol.Length(min=1, max=64)),
        vol.Required("date"): vol.All(str, vol.Length(min=10, max=10)),
    }
)
@websocket_api.async_response
async def ws_list_sd_records(hass, connection, msg: dict[str, Any]) -> None:
    """Return one day's recorded ranges; there is no playback here."""
    day = requested_day(msg["date"], dt_util.now().date())
    if day is None:
        connection.send_error(msg["id"], "invalid_format", "Choose a day in the last week")
        return
    resolved = resolve(hass, msg["entry_id"])
    if resolved is None:
        connection.send_error(msg["id"], "not_found", "EZVIZ bridge is not loaded")
        return
    entry, runtime = resolved
    result = {"supported": False, "date": day.isoformat(), "records": []}
    try:
        await async_verify_native(entry, runtime.client)
        records = await runtime.client.ezviz_sd_records(entry.data[CONF_ALIAS], day)
    except EzvizFeatureUnsupportedError:
        connection.send_result(msg["id"], result)
        return
    except BridgeError:
        connection.send_error(msg["id"], "unavailable", "microSD records are unavailable")
        return
    result["supported"] = True
    result["records"] = [
        {"start": record.start, "end": record.end, "type": record.record_type} for record in records
    ]
    connection.send_result(msg["id"], result)


@callback
def async_register(hass: HomeAssistant) -> None:
    websocket_api.async_register_command(hass, ws_list_sd_records)
