"""Authenticated streaming proxy for provider-local video recordings."""

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant, callback

from . import BridgeRuntime
from .const import CONF_PROVIDER, DOMAIN, PROVIDER_EZVIZ
from .errors import BridgeError


class ProviderRecordingView(HomeAssistantView):
    """Relay one immutable recording through HA auth or a signed path."""

    url = "/api/media_bridge/ezviz/recordings/{entry_id}/{recording_id}"
    name = "api:media_bridge:ezviz-recording"
    requires_auth = True

    async def get(
        self,
        request: web.Request,
        entry_id: str,
        recording_id: str,
    ) -> web.StreamResponse:
        hass: HomeAssistant = request.app["hass"]
        entry = hass.config_entries.async_get_entry(entry_id)
        runtime = hass.data.get(DOMAIN, {}).get(entry_id)
        if (
            entry is None
            or entry.data.get(CONF_PROVIDER) != PROVIDER_EZVIZ
            or not isinstance(runtime, BridgeRuntime)
            or runtime.client is None
        ):
            raise web.HTTPNotFound
        try:
            upstream = await runtime.client.open_provider_recording(recording_id)
        except BridgeError as error:
            raise web.HTTPNotFound from error
        if upstream.status != 200 or upstream.content_type != "video/mpeg":
            upstream.release()
            raise web.HTTPNotFound
        response = web.StreamResponse(
            status=200,
            headers={
                "Cache-Control": "no-store",
                "Content-Type": "video/mpeg",
                "X-Content-Type-Options": "nosniff",
            },
        )
        await response.prepare(request)
        try:
            async for chunk in upstream.content.iter_chunked(64 * 1024):
                await response.write(chunk)
        except (ConnectionError, RuntimeError):
            pass
        finally:
            upstream.close()
        return response


@callback
def async_register(hass: HomeAssistant) -> None:
    """Register the provider recording relay exactly once."""
    hass.http.register_view(ProviderRecordingView)
