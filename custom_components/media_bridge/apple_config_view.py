"""Authenticated non-secret discovery for the Vistoda Apple companion."""

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

from . import BridgeRuntime
from .const import CONF_PROVIDER, DOMAIN, PROVIDER_RING
from .ring_relay_contract import PROTOCOL

CONFIG_PATH = "/api/media_bridge/apple/config"


class AppleConfigView(HomeAssistantView):
    """List loaded Ring config entries without bridge details."""

    url = CONFIG_PATH
    name = "api:media_bridge:apple_config"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        """Return the minimum native client configuration."""
        hass: HomeAssistant = request.app["hass"]
        entries = []
        for entry in hass.config_entries.async_entries(DOMAIN):
            runtime = hass.data.get(DOMAIN, {}).get(entry.entry_id)
            if entry.data.get(CONF_PROVIDER) != PROVIDER_RING or not isinstance(
                runtime, BridgeRuntime
            ):
                continue
            entries.append(
                {
                    "entry_id": entry.entry_id,
                    "name": entry.title,
                    "open_door_service": f"{DOMAIN}.open_ring_door",
                }
            )
        return web.json_response(
            {"protocol": PROTOCOL, "ring": entries},
            headers={"Cache-Control": "no-store"},
        )


def async_register(hass: HomeAssistant) -> None:
    """Register discovery once during integration setup."""
    hass.http.register_view(AppleConfigView)
