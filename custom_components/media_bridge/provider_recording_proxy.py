"""Authenticated streaming proxy for provider-local video recordings."""

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant, callback

from . import BridgeRuntime
from .const import CONF_ALIAS, CONF_PROVIDER, DOMAIN, PROVIDER_EZVIZ
from .errors import BridgeError
from .ezviz_binding import async_verify_native


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
        runtime = await _owned_runtime(request, entry_id, recording_id)
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


class ProviderPlaybackView(HomeAssistantView):
    """Relay a browser-compatible fragmented MP4 without persisting a duplicate."""

    url = "/api/media_bridge/ezviz/recordings/{entry_id}/{recording_id}/playback.mp4"
    name = "api:media_bridge:ezviz-recording-playback"
    requires_auth = True

    async def get(self, request, entry_id: str, recording_id: str) -> web.StreamResponse:
        runtime = await _owned_runtime(request, entry_id, recording_id)
        try:
            upstream = await runtime.client.open_provider_playback(recording_id)
        except BridgeError as error:
            raise web.HTTPNotFound from error
        if upstream.status != 200 or upstream.content_type != "video/mp4":
            upstream.release()
            raise web.HTTPNotFound
        return await _relay(request, upstream, "video/mp4")


def _runtime(request: web.Request, entry_id: str) -> BridgeRuntime:
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
    return runtime


async def _owned_runtime(
    request: web.Request,
    entry_id: str,
    recording_id: str,
) -> BridgeRuntime:
    """Resolve a recording only when it belongs to the selected camera entry."""
    hass: HomeAssistant = request.app["hass"]
    entry = hass.config_entries.async_get_entry(entry_id)
    runtime = _runtime(request, entry_id)
    try:
        await async_verify_native(entry, runtime.client)
        manifest = await runtime.client.provider_recording(recording_id)
    except BridgeError as error:
        raise web.HTTPNotFound from error
    if entry is None or manifest.get("camera") != entry.data.get(CONF_ALIAS):
        raise web.HTTPNotFound
    return runtime


async def _relay(request: web.Request, upstream, content_type: str) -> web.StreamResponse:
    response = web.StreamResponse(
        status=200,
        headers={
            "Cache-Control": "no-store",
            "Content-Type": content_type,
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
    hass.http.register_view(ProviderPlaybackView)
