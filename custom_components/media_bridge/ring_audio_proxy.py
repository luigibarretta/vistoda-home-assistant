"""Authenticated HTTP WebSocket proxy for native Apple Ring audio."""

from __future__ import annotations

import asyncio
from contextlib import suppress

from aiohttp import ClientError, WSMsgType, web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

from . import BridgeRuntime
from .const import CONF_ALIAS, CONF_PROVIDER, DOMAIN, PROVIDER_RING
from .ring_relay_contract import (
    MAX_MESSAGE_BYTES,
    MAX_SESSION_SECONDS,
    valid_client_binary,
    valid_server_binary,
    valid_text,
)

PROXY_URL = "/api/media_bridge/ring/audio/{entry_id}"


class RingAudioRelayView(HomeAssistantView):
    """Terminate HA auth and proxy bounded PCMU frames to the private bridge."""

    url = PROXY_URL
    name = "api:media_bridge:ring_audio_relay"
    requires_auth = True

    async def get(self, request: web.Request, entry_id: str) -> web.StreamResponse:
        """Upgrade only a loaded Ring entry for an authenticated HA user."""
        hass: HomeAssistant = request.app["hass"]
        resolved = resolve_ring(hass, entry_id)
        if resolved is None:
            raise web.HTTPNotFound
        runtime, alias = resolved
        try:
            async with runtime.client.ring_relay(alias) as upstream:
                downstream = web.WebSocketResponse(
                    heartbeat=15,
                    max_msg_size=MAX_MESSAGE_BYTES,
                    receive_timeout=MAX_SESSION_SECONDS,
                )
                await downstream.prepare(request)
                await relay(downstream, upstream)
                return downstream
        except (ClientError, TimeoutError) as error:
            raise web.HTTPBadGateway from error


def async_register(hass: HomeAssistant) -> None:
    """Register the authenticated relay view once during integration setup."""
    hass.http.register_view(RingAudioRelayView)


def resolve_ring(hass: HomeAssistant, entry_id: str) -> tuple[BridgeRuntime, str] | None:
    """Resolve one loaded Ring bridge without returning its token."""
    entry = hass.config_entries.async_get_entry(entry_id)
    runtime = hass.data.get(DOMAIN, {}).get(entry_id)
    if (
        entry is None
        or entry.data.get(CONF_PROVIDER) != PROVIDER_RING
        or not isinstance(runtime, BridgeRuntime)
        or runtime.client is None
    ):
        return None
    return runtime, entry.data[CONF_ALIAS]


async def relay(downstream: web.WebSocketResponse, upstream) -> None:
    """Run two bounded pumps and tear both sides down when either stops."""
    tasks = {
        asyncio.create_task(client_to_bridge(downstream, upstream)),
        asyncio.create_task(bridge_to_client(upstream, downstream)),
    }
    try:
        done, _pending = await asyncio.wait(
            tasks,
            timeout=MAX_SESSION_SECONDS,
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in done:
            with suppress(asyncio.CancelledError, ClientError, ConnectionError, RuntimeError):
                task.result()
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        with suppress(ClientError, RuntimeError):
            await upstream.close()
        if not downstream.closed:
            await downstream.close()


async def client_to_bridge(downstream: web.WebSocketResponse, upstream) -> None:
    """Forward only exact PCMU frames and bounded control text."""
    async for message in downstream:
        if message.type == WSMsgType.BINARY and valid_client_binary(message.data):
            await upstream.send_bytes(message.data)
        elif message.type == WSMsgType.TEXT and valid_text(message.data):
            await upstream.send_str(message.data)
        elif message.type in {WSMsgType.PING, WSMsgType.PONG}:
            continue
        else:
            break


async def bridge_to_client(upstream, downstream: web.WebSocketResponse) -> None:
    """Forward only bounded bridge lifecycle and PCMU messages."""
    async for message in upstream:
        if message.type == WSMsgType.BINARY and valid_server_binary(message.data):
            await downstream.send_bytes(message.data)
        elif message.type == WSMsgType.TEXT and valid_text(message.data):
            await downstream.send_str(message.data)
        elif message.type in {WSMsgType.PING, WSMsgType.PONG}:
            continue
        else:
            break
