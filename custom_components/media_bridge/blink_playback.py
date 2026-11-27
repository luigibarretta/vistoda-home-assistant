"""Play Blink HA-local recordings in the browser: MPEG-TS converted to MP4 on demand."""

import re

from aiohttp import web
from homeassistant.components.http import HomeAssistantView

from .ts_remux import MAX_REMUX_BYTES, ts_to_mp4

SAFE_ID = re.compile(r"^[0-9a-f-]{36}$")
RANGE = re.compile(r"^bytes=(\d*)-(\d*)$")
HEADERS = {
    "Cache-Control": "no-store",
    "Content-Type": "video/mp4",
    "X-Content-Type-Options": "nosniff",
    "Accept-Ranges": "bytes",
}


def mp4_response(request: web.Request, data: bytes) -> web.Response:
    """Whole file, or one byte range, so the browser can seek."""
    total = len(data)
    match = RANGE.match(request.headers.get("Range", ""))
    if match is None or not any(match.groups()):
        return web.Response(body=data, headers=HEADERS)
    first, last = match.groups()
    if first:
        start, end = int(first), min(int(last) if last else total - 1, total - 1)
    else:  # "-N": the last N bytes
        start, end = max(total - int(last), 0), total - 1
    if start > end or start >= total:
        return web.Response(status=416, headers={"Content-Range": f"bytes */{total}"})
    return web.Response(
        status=206,
        body=data[start : end + 1],
        headers={**HEADERS, "Content-Range": f"bytes {start}-{end}/{total}"},
    )


class BlinkRecordingPlayback(HomeAssistantView):
    """A Blink HA-local recording as MP4, converted from the app's MPEG-TS archive."""

    url = "/api/media_bridge/blink/recordings/{recording_id}/playback.mp4"
    name = "api:media_bridge:blink-recording-playback"
    requires_auth = True

    async def get(self, request: web.Request, recording_id: str) -> web.Response:
        hass = request.app["hass"]
        runtime = hass.data.get("blink_live_bridge", {}).get("runtime")
        if runtime is None or not SAFE_ID.fullmatch(recording_id):
            raise web.HTTPNotFound
        try:
            upstream = await runtime.client.stream(f"/v1/recordings/{recording_id}/media")
        except Exception as error:  # Engine errors use integration-specific types.
            raise web.HTTPNotFound from error
        chunks: list[bytes] = []
        size = 0
        try:
            if upstream.status != 200:
                raise web.HTTPNotFound
            async for chunk in upstream.content.iter_chunked(256 * 1024):
                size += len(chunk)
                if size > MAX_REMUX_BYTES:
                    raise web.HTTPRequestEntityTooLarge(max_size=MAX_REMUX_BYTES, actual_size=size)
                chunks.append(chunk)
        finally:
            upstream.release()
        try:
            data = await hass.async_add_executor_job(ts_to_mp4, b"".join(chunks))
        except ValueError as error:
            raise web.HTTPUnsupportedMediaType from error
        return mp4_response(request, data)
