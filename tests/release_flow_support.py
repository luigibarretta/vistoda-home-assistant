"""Executable flow boundaries with isolated HA framework doubles."""

import importlib
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock


def framework(monkeypatch):
    def module(name, **values):
        result = ModuleType(name)
        result.__dict__.update(values)
        monkeypatch.setitem(sys.modules, name, result)
        return result

    class FlowBase:
        def __init_subclass__(cls, **kwargs):
            pass

        def async_show_form(self, **kwargs):
            return {"type": "form", **kwargs}

        def async_abort(self, **kwargs):
            return {"type": "abort", **kwargs}

        def async_create_entry(self, **kwargs):
            return {"type": "create_entry", **kwargs}

        def async_update_reload_and_abort(self, entry, **kwargs):
            self.updated = entry, kwargs
            return {"type": "abort", "reason": kwargs.get("reason")}

        async def async_set_unique_id(self, unique_id):
            self.unique_id = unique_id

        def _abort_if_unique_id_configured(self):
            pass

        def _get_reauth_entry(self):
            return self.hass.config_entries.async_get_entry(self.context["entry_id"])

        _get_reconfigure_entry = _get_reauth_entry

    def marker(value, **kwargs):
        return value

    def identity(value):
        return value

    module(
        "voluptuous",
        Schema=identity,
        Optional=marker,
        Required=marker,
        In=identity,
        All=lambda *args: args,
        Length=lambda **kwargs: kwargs,
        Match=identity,
        Range=lambda **kwargs: kwargs,
        Any=lambda *args: args,
    )
    config_entries = module(
        "homeassistant.config_entries",
        ConfigFlow=FlowBase,
        OptionsFlow=FlowBase,
        ConfigEntry=object,
        SOURCE_USER="user",
    )
    module("homeassistant", config_entries=config_entries)
    module("homeassistant.data_entry_flow", FlowResult=dict)
    module("homeassistant.helpers.aiohttp_client", async_get_clientsession=lambda hass: None)
    module("homeassistant.helpers.service_info.zeroconf", ZeroconfServiceInfo=object)
    module("homeassistant.helpers.service_info.hassio", HassioServiceInfo=object)
    module("homeassistant.core", HomeAssistant=object, callback=identity)
    websocket = SimpleNamespace(
        websocket_command=lambda schema: identity,
        async_response=identity,
        async_register_command=lambda *args: None,
    )
    module("homeassistant.components", websocket_api=websocket)
    module("custom_components.media_bridge.local", blink_adapter_available=lambda hass: True)
    module(
        "custom_components.media_bridge.schemas",
        bridge_schema=lambda *args: {},
        discovered_schema=lambda: {},
        provider_schema=lambda: {},
        otp_schema=lambda: {},
        ring_credentials_schema=lambda: {},
        ezviz_credentials_schema=lambda: {},
    )
    monkeypatch.setattr(
        sys.modules["custom_components.media_bridge"],
        "BridgeRuntime",
        SimpleNamespace,
        raising=False,
    )

    def load(name):
        full = f"custom_components.media_bridge.{name}"
        monkeypatch.delitem(sys.modules, full, raising=False)
        imported = importlib.import_module(full)
        del sys.modules[full]
        monkeypatch.setitem(sys.modules, full, imported)
        return imported

    for name in ("ring_flow", "ezviz_flow", "managed_flow", "options_flow", "ring_inventory_flow"):
        load(name)
    flow_class = load("config_flow").ConfigFlow
    entries = {}

    def update(entry, **kwargs):
        changed = any(getattr(entry, key) != value for key, value in kwargs.items())
        for key, value in kwargs.items():
            setattr(entry, key, value)
        return changed

    async def executor(func, *args):
        return func(*args)

    hass = SimpleNamespace(
        data={},
        async_add_executor_job=executor,
        config_entries=SimpleNamespace(
            async_get_entry=entries.get,
            async_entries=lambda domain: list(entries.values()),
            async_update_entry=update,
            async_reload=AsyncMock(),
            flow=SimpleNamespace(async_init=AsyncMock()),
        ),
    )

    def make_flow(entry=None):
        flow = flow_class()
        flow.hass = hass
        flow.context = (
            {"source": "reauth", "entry_id": entry.entry_id} if entry else {"source": "hassio"}
        )
        if entry:
            entries[entry.entry_id] = entry
        flow._validated_client = AsyncMock(
            return_value=SimpleNamespace(
                start_ring_enrollment=AsyncMock(),
                start_ezviz_enrollment=AsyncMock(),
                verify_enrollment=AsyncMock(),
                ring_status=AsyncMock(),
                ring_intercoms=AsyncMock(
                    return_value=[
                        {
                            "alias": "north",
                            "device_id": "111",
                            "name": "North",
                            "location_name": "Home",
                        },
                        {
                            "alias": "south",
                            "device_id": "222",
                            "name": "South",
                            "location_name": "Home",
                        },
                    ]
                ),
            )
        )
        return flow

    return SimpleNamespace(
        load=load, make_flow=make_flow, hass=hass, entries=entries, module=module
    )


def entry(provider="ring", key="entry-a", **extra):
    return SimpleNamespace(
        entry_id=key,
        title="My entrance",
        unique_id="old-unique-id",
        options={"backup_storage": "family_archive"},
        data={
            "provider": provider,
            "alias": "entrance",
            "url": "http://bridge.local:8787",
            "api_token": "x" * 32,
            "managed_app": True,
            **extra,
        },
    )
