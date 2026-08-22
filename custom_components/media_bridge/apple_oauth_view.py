"""Same-origin OAuth callback for the native Vistoda Apple companion."""

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

from .apple_oauth_contract import CALLBACK_PATH, native_callback


class AppleOAuthCallbackView(HomeAssistantView):
    """Redirect one bounded HA authorization result to the installed app."""

    url = CALLBACK_PATH
    name = "api:media_bridge:apple_oauth_callback"
    requires_auth = False

    async def get(self, request: web.Request) -> web.StreamResponse:
        """Forward only code/error and state to the private custom scheme."""
        location = native_callback(request.rel_url.query)
        if location is None:
            raise web.HTTPBadRequest
        raise web.HTTPFound(
            location=location,
            headers={
                "Cache-Control": "no-store",
                "Referrer-Policy": "no-referrer",
            },
        )


def async_register(hass: HomeAssistant) -> None:
    """Register the callback once during integration setup."""
    hass.http.register_view(AppleOAuthCallbackView)
