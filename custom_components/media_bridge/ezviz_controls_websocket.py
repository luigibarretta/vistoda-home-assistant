"""Settings and PTZ through the Vistoda EZVIZ app's own EZVIZ login (0.10+)."""

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api

from .client_ezviz_controls import (
    PTZ_DIRECTIONS,
    EzvizControlConflictError,
    EzvizControlUnconfirmedError,
)
from .const import CONF_ALIAS, CONF_PROVIDER, DOMAIN, PROVIDER_EZVIZ
from .errors import BridgeError, ReauthRequiredError
from .ezviz_binding import async_verify_native
from .ezviz_controls import controls_of, supports_controls
from .ezviz_controls_settings import control_key, settings_from_controls, valid_value

# The app is reachable but failing: never silently switch to the native session.
APP_FAILED = object()


def _resolve(hass, entry_id: str):
    """Return (entry, runtime) for a loaded EZVIZ camera entry, else None."""
    entry = hass.config_entries.async_get_entry(entry_id)
    runtime = getattr(hass, "data", {}).get(DOMAIN, {}).get(entry_id)
    if entry is None or entry.data.get(CONF_PROVIDER) != PROVIDER_EZVIZ:
        return None
    return (entry, runtime) if getattr(runtime, "client", None) is not None else None


async def app_source(hass, entry_id: str):
    """Return (entry, runtime) when the app owns the controls, None for the native path."""
    resolved = _resolve(hass, entry_id)
    coordinator = getattr(resolved[1], "ezviz_controls", None) if resolved else None
    if coordinator is None:
        return None
    if coordinator.data is None or not coordinator.last_update_success:
        # First use before the deferred poll, or a transient failure: ask once now.
        await coordinator.async_refresh()
    if not supports_controls(coordinator.data):
        return None  # A 404 (older app) or an app that never answered: native path.
    return resolved if coordinator.last_update_success else APP_FAILED


async def async_app_info(hass, connection, msg: dict[str, Any]) -> bool:
    """Answer settings/info from the app; False hands the request to the native path."""
    source = await app_source(hass, msg["entry_id"])
    if source is None:
        return False
    if source is APP_FAILED:
        connection.send_error(msg["id"], "unavailable", "EZVIZ settings are unavailable")
        return True
    controls = controls_of(source[1].ezviz_controls.data)
    connection.send_result(
        msg["id"], {"settings": settings_from_controls(controls), "source": "vistoda"}
    )
    return True


async def async_app_set(hass, connection, msg: dict[str, Any]) -> bool:
    """Compare-and-set through the app; False hands the request to the native path."""
    source = await app_source(hass, msg["entry_id"])
    if source is None:
        return False
    if source is APP_FAILED:
        connection.send_error(msg["id"], "unavailable", "EZVIZ settings are unavailable")
        return True
    entry, runtime = source
    coordinator = runtime.ezviz_controls
    controls = controls_of(coordinator.data)
    key, value, expected = msg["key"], msg["value"], msg["expected_value"]
    app_key = control_key(key, controls)
    if app_key is None:
        connection.send_error(msg["id"], "not_supported", "EZVIZ setting is read-only")
        return True
    if not valid_value(key, value, controls) or not valid_value(key, expected, controls):
        connection.send_error(msg["id"], "invalid_format", "Unsupported EZVIZ setting value")
        return True
    error = None
    try:
        await async_verify_native(entry, runtime.client)
        confirmed = await runtime.client.ezviz_set_control(
            entry.data[CONF_ALIAS], app_key, value, expected
        )
    except EzvizControlConflictError:
        error = ("conflict", "EZVIZ setting changed upstream")
    except EzvizControlUnconfirmedError:
        # The app could not read the write back and restored the previous value.
        error = ("unconfirmed", "EZVIZ did not confirm the setting")
    except ReauthRequiredError:
        entry.async_start_reauth(hass)
        error = ("reauth_required", "The Vistoda EZVIZ login must be renewed")
    except BridgeError:
        error = ("unavailable", "EZVIZ rejected the setting")
    if error is not None:
        # Poll again so the panel's follow-up settings/info shows the real state.
        await coordinator.async_refresh()
        connection.send_error(msg["id"], *error)
        return True
    coordinator.async_apply(confirmed)
    connection.send_result(
        msg["id"], {"settings": settings_from_controls(confirmed), "source": "vistoda"}
    )
    return True


@websocket_api.websocket_command(
    {
        vol.Required("type"): "media_bridge/ezviz/ptz",
        vol.Required("entry_id"): vol.All(str, vol.Length(min=1, max=64)),
        vol.Required("direction"): vol.In(PTZ_DIRECTIONS),
    }
)
@websocket_api.async_response
async def ws_ptz(hass, connection, msg: dict[str, Any]) -> None:
    """One PTZ step through the app; the panel uses native buttons for older apps."""
    source = await app_source(hass, msg["entry_id"])
    controls = controls_of(source[1].ezviz_controls.data) if isinstance(source, tuple) else None
    if controls is None or not controls.ptz:
        connection.send_error(msg["id"], "not_supported", "PTZ is not available")
        return
    entry, runtime = source
    try:
        await async_verify_native(entry, runtime.client)
        await runtime.client.ezviz_ptz(entry.data[CONF_ALIAS], msg["direction"])
    except EzvizControlConflictError:
        connection.send_error(msg["id"], "not_supported", "PTZ is not available")
        return
    except BridgeError:
        connection.send_error(msg["id"], "unavailable", "PTZ command failed")
        return
    connection.send_result(msg["id"], {"direction": msg["direction"]})
