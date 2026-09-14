"""Read-only native EZVIZ metadata, matched to the immutable camera binding."""

from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .ezviz_binding import CONF_EZVIZ_SOURCE_ID, valid_source_id


def _native_entity(hass, entity) -> dict:
    state = hass.states.get(entity.entity_id)
    attributes = state.attributes if state else {}
    return {
        "entity_id": entity.entity_id,
        "domain": entity.entity_id.partition(".")[0],
        "name": (
            attributes.get("friendly_name")
            or entity.name
            or entity.original_name
            or entity.entity_id
        )[:255],
        "device_class": (
            attributes.get("device_class") or entity.original_device_class
        ),
    }


def panel_metadata(hass, entry) -> dict:
    """Do not guess the account from a friendly name or a shared alias."""
    source = entry.data.get(CONF_EZVIZ_SOURCE_ID)
    if not valid_source_id(source):
        return {}
    serial = source.rsplit(":", 1)[0]
    matches = []
    for native in hass.config_entries.async_entries("ezviz"):
        coordinator = getattr(native, "runtime_data", None)
        data = getattr(coordinator, "data", None)
        if isinstance(data, dict) and isinstance(data.get(serial), dict):
            matches.append((native, data[serial]))
    if len(matches) != 1:
        return {}
    native, data = matches[0]
    result = {}
    if isinstance(data.get("name"), str) and data["name"].strip():
        result["device_name"] = data["name"][:255]
    registry = er.async_get(hass)
    alarms = [
        entity.entity_id
        for entity in registry.entities.values()
        if entity.config_entry_id == native.entry_id
        and entity.disabled_by is None
        and entity.entity_id.startswith("alarm_control_panel.")
    ]
    if len(alarms) == 1:
        result["alarm_entity_id"] = alarms[0]
        result["alarm_scope"] = "account"
    device = dr.async_get(hass).async_get_device_by_identifier(("ezviz", serial), native.entry_id)
    if device:
        native_entities = sorted(
            (
                _native_entity(hass, entity)
                for entity in registry.entities.values()
                if entity.config_entry_id == native.entry_id
                and entity.device_id == device.id
                and entity.disabled_by is None
            ),
            key=lambda item: (item["domain"], item["name"], item["entity_id"]),
        )
        result["native_entities"] = native_entities[:64]
        batteries = [
            item["entity_id"]
            for item in native_entities
            if item["device_class"] == "battery"
        ]
        if len(batteries) == 1:
            result["battery_entity_id"] = batteries[0]
    if device and device.area_id:
        area = ar.async_get(hass).async_get_area(device.area_id)
        if area:
            result["room_name"] = area.name
            result["room_source"] = "home_assistant"
    return result
