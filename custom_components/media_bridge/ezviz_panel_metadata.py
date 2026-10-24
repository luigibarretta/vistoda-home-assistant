"""Read-only native EZVIZ registry metadata, matched to the immutable camera binding."""

from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import entity_registry as er

from .ezviz_core import bound_serial, native_device, native_entities

# Unique-id suffixes of HA core EZVIZ entities (2026.8, pyezvizapi 1.0.0.7):
# buttons/number use "{serial}_{key}", binary sensors "{serial}_{name}.{key}".
ROLE_SUFFIXES = {
    "_ptz_up": "ptz_up",
    "_ptz_down": "ptz_down",
    "_ptz_left": "ptz_left",
    "_ptz_right": "ptz_right",
    "_detection_sensibility": "detection_sensitivity",
    ".alarm_schedules_enabled": "alarm_schedule",
    ".encrypted": "encrypted",
}


def entity_role(serial: str, unique_id) -> str | None:
    """Map a native unique_id to a stable panel role, never by entity_id or name."""
    if not isinstance(unique_id, str) or not unique_id.startswith(f"{serial}_"):
        return None
    return next(
        (role for suffix, role in ROLE_SUFFIXES.items() if unique_id.endswith(suffix)), None
    )


def _native_entity(hass, entity, serial: str = "") -> dict:
    state = hass.states.get(entity.entity_id)
    attributes = state.attributes if state else {}
    role = entity_role(serial, getattr(entity, "unique_id", None))
    return {
        **({"role": role} if role else {}),
        "entity_id": entity.entity_id,
        "domain": entity.entity_id.partition(".")[0],
        "name": (
            attributes.get("friendly_name")
            or entity.name
            or entity.original_name
            or entity.entity_id
        )[:255],
        "device_class": (attributes.get("device_class") or entity.original_device_class),
    }


def panel_metadata(hass, entry) -> dict:
    """Do not guess the account from a friendly name or a shared alias."""
    resolved = native_device(hass, entry)
    if resolved is None:
        return {}
    device, native = resolved
    serial = bound_serial(entry)
    result = {}
    name = device.name_by_user or device.name
    if isinstance(name, str) and name.strip():
        result["device_name"] = name[:255]
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
    entities = sorted(
        (_native_entity(hass, entity, serial) for entity in native_entities(hass, device, native)),
        key=lambda item: (item["domain"], item["name"], item["entity_id"]),
    )
    result["native_entities"] = entities[:64]
    batteries = [item["entity_id"] for item in entities if item["device_class"] == "battery"]
    if len(batteries) == 1:
        result["battery_entity_id"] = batteries[0]
    if device.area_id:
        area = ar.async_get(hass).async_get_area(device.area_id)
        if area:
            result["room_name"] = area.name
            result["room_source"] = "home_assistant"
    return result
