"""Authenticated, secret-free inventory for the Vistoda panel."""

from collections import Counter
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import (
    BLINK_BRIDGE_DOMAIN,
    CONF_PROVIDER,
    DOMAIN,
    PROVIDERS,
)

MAX_ENTITIES_PER_PROVIDER = 256


@callback
def async_register(hass: HomeAssistant) -> None:
    """Register the bounded panel inventory command."""
    websocket_api.async_register_command(hass, ws_panel_info)


@websocket_api.websocket_command({vol.Required("type"): "media_bridge/panel/info"})
@callback
def ws_panel_info(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return provider, device and entity metadata without private endpoints."""
    providers, entry_providers = _provider_inventory(hass)
    entities = er.async_get(hass)
    devices = dr.async_get(hass)
    grouped: dict[str, dict[str, dict[str, Any]]] = {provider: {} for provider in PROVIDERS}
    seen = Counter()
    for entity in entities.entities.values():
        provider = entry_providers.get(entity.config_entry_id)
        if provider is None or entity.disabled_by is not None:
            continue
        if seen[provider] >= MAX_ENTITIES_PER_PROVIDER:
            providers[provider]["truncated"] = True
            continue
        seen[provider] += 1
        device_id = entity.device_id or f"{provider}:unassigned"
        device = devices.devices.get(entity.device_id) if entity.device_id else None
        group = grouped[provider].setdefault(
            device_id,
            {
                "device_id": entity.device_id,
                "name": _device_name(device, provider),
                "manufacturer": getattr(device, "manufacturer", None),
                "model": getattr(device, "model", None),
                "entities": {},
            },
        )
        domain = entity.entity_id.partition(".")[0]
        group["entities"].setdefault(domain, []).append(_entity_info(hass, entity))
    for provider in PROVIDERS:
        provider_devices = sorted(grouped[provider].values(), key=lambda item: item["name"])
        counts = Counter()
        for device in provider_devices:
            for domain, domain_entities in device["entities"].items():
                domain_entities.sort(key=lambda item: item["name"])
                counts[domain] += len(domain_entities)
        providers[provider]["devices"] = provider_devices
        providers[provider]["counts"] = dict(sorted(counts.items()))
    connection.send_result(msg["id"], {"providers": providers})


def _provider_inventory(hass: HomeAssistant) -> tuple[dict, dict[str, str]]:
    providers = {
        provider: {
            "configured": False,
            "available": False,
            "title": f"Vistoda · {provider.upper()}",
            "truncated": False,
        }
        for provider in PROVIDERS
    }
    entry_providers: dict[str, str] = {}
    for entry in hass.config_entries.async_entries(DOMAIN):
        provider = entry.data.get(CONF_PROVIDER)
        if provider not in PROVIDERS:
            continue
        entry_providers[entry.entry_id] = provider
        providers[provider]["configured"] = True
        providers[provider]["title"] = entry.title
        runtime = hass.data.get(DOMAIN, {}).get(entry.entry_id)
        coordinator = getattr(runtime, "coordinator", None)
        providers[provider]["available"] = bool(coordinator and coordinator.last_update_success)
    for entry in hass.config_entries.async_entries(BLINK_BRIDGE_DOMAIN):
        entry_providers[entry.entry_id] = "blink"
        providers["blink"]["configured"] = True
        runtime = hass.data.get(BLINK_BRIDGE_DOMAIN, {}).get(entry.entry_id)
        coordinator = getattr(runtime, "coordinator", None)
        if coordinator and coordinator.last_update_success:
            providers["blink"]["available"] = True
    return providers, entry_providers


def _device_name(device, provider: str) -> str:
    if device is None:
        return f"Vistoda · {provider.upper()}"
    return (
        getattr(device, "name_by_user", None)
        or getattr(device, "name", None)
        or f"Vistoda · {provider.upper()}"
    )


def _entity_info(hass: HomeAssistant, entity) -> dict[str, Any]:
    state = hass.states.get(entity.entity_id)
    attributes = state.attributes if state else {}
    name = (
        attributes.get("friendly_name")
        or getattr(entity, "name", None)
        or getattr(entity, "original_name", None)
    )
    return {
        "entity_id": entity.entity_id,
        "name": name or entity.entity_id,
        "device_class": attributes.get("device_class")
        or getattr(entity, "original_device_class", None),
        "available": bool(state and state.state not in {STATE_UNAVAILABLE, STATE_UNKNOWN}),
    }
