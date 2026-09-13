"""Execute camera handlers with isolated HA decorators and deterministic timers.

The admin decorator models Core's permission boundary; these tests verify that
the handlers use it, not the implementation of Home Assistant's decorator.
"""

import asyncio
import importlib
import sys
from functools import wraps
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, Mock


class Timer:
    def __init__(self, delay, callback):
        self.delay, self.callback, self.cancelled = delay, callback, False

    def cancel(self):
        self.cancelled = True


def connection(*, admin=True):
    return SimpleNamespace(
        user=SimpleNamespace(is_admin=admin),
        subscriptions={},
        send_result=Mock(),
        send_error=Mock(),
    )


def message(number=1, *, entry="account", camera="51", session="synthetic-session"):
    return {
        "id": number,
        "entry_id": entry,
        "camera_id": camera,
        "session_id": session,
        "offer_sdp": "synthetic-offer",
        "mode": "listen",
        "ice_gathering_ms": 5,
    }


def boundary(monkeypatch):
    def module(name, **values):
        result = ModuleType(name)
        result.__dict__.update(values)
        monkeypatch.setitem(sys.modules, name, result)
        return result

    def require_admin(handler):
        @wraps(handler)
        async def guarded(hass, owner, msg):
            if not owner.user.is_admin:
                raise PermissionError("admin required")
            return await handler(hass, owner, msg)

        return guarded

    module(
        "voluptuous",
        Required=lambda value: value,
        Optional=lambda value: value,
        All=lambda *args: args,
        Match=lambda value: value,
        In=lambda value: value,
        Length=lambda **kwargs: tuple(kwargs.items()),
        Range=lambda **kwargs: tuple(kwargs.items()),
    )
    websocket_api = module(
        "homeassistant.components.websocket_api",
        websocket_command=lambda _: lambda handler: handler,
        async_response=lambda handler: handler,
        require_admin=require_admin,
        async_register_command=Mock(),
    )
    module("homeassistant")
    module("homeassistant.components", websocket_api=websocket_api)
    module("homeassistant.core", callback=lambda handler: handler)
    package = sys.modules["custom_components.media_bridge"]
    name = "custom_components.media_bridge.ring_camera_websocket"
    monkeypatch.setattr(package, "ring_camera_websocket", None, raising=False)
    monkeypatch.delitem(sys.modules, name, raising=False)
    api = importlib.import_module(name)
    del sys.modules[name]
    monkeypatch.setitem(sys.modules, name, api)
    client = object()
    monkeypatch.setattr(api, "resolve", Mock(return_value=client))
    result = {
        "session_id": "synthetic-session",
        "answer_sdp": "v=0\r\n",
        "ice_candidates": [],
        "expires_in": 120,
    }
    monkeypatch.setattr(api.camera, "start", AsyncMock(return_value=result))
    monkeypatch.setattr(api.camera, "stop", AsyncMock())
    monkeypatch.setattr(api.camera, "cameras", AsyncMock(return_value=[]))
    timers, tasks = [], []

    def call_later(delay, callback):
        timer = Timer(delay, callback)
        timers.append(timer)
        return timer

    def create_task(coroutine):
        task = asyncio.create_task(coroutine)
        tasks.append(task)
        return task

    monkeypatch.setattr(
        api,
        "asyncio",
        SimpleNamespace(get_running_loop=lambda: SimpleNamespace(call_later=call_later)),
    )
    hass = SimpleNamespace(data={}, async_create_task=create_task)

    async def drain():
        if tasks:
            await asyncio.gather(*tasks)
            tasks.clear()

    return SimpleNamespace(
        api=api,
        hass=hass,
        client=client,
        timers=timers,
        result=result,
        drain=drain,
        registration=websocket_api.async_register_command,
    )
