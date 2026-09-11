"""Entry-scoped EZVIZ identity and non-destructive legacy registry migration."""

from .const import CONF_ALIAS, DOMAIN


def entity_prefix(entry) -> str:
    return f"ezviz-{entry.entry_id}-"


def device_identifier(entry) -> tuple[str, str]:
    return DOMAIN, f"ezviz:{entry.entry_id}"


def device_info(entry) -> dict:
    return {
        "identifiers": {device_identifier(entry)},
        "name": f"Vistoda · EZVIZ · {entry.data[CONF_ALIAS]}",
        "manufacturer": "EZVIZ",
        "model": "Vistoda camera bridge",
    }


def async_migrate_registry(hass, entry) -> None:
    """Retain entity IDs, names and device references wherever unambiguous."""
    from homeassistant.helpers import device_registry as dr
    from homeassistant.helpers import entity_registry as er

    registry = er.async_get(hass)
    legacy_prefix = f"ezviz-{entry.data[CONF_ALIAS]}-"
    changes = []
    for entity in list(registry.entities.values()):
        if entity.config_entry_id != entry.entry_id or entity.platform != DOMAIN:
            continue
        if entity.unique_id in {
            f"{legacy_prefix}bridge-camera",
            f"{legacy_prefix}bridge-connectivity",
        }:
            unique_id = entity_prefix(entry) + entity.unique_id.removeprefix(legacy_prefix)
            conflict = registry.async_get_entity_id(entity.domain, DOMAIN, unique_id)
            if conflict is not None and conflict != entity.entity_id:
                raise ValueError("EZVIZ registry identity collision")
            changes.append((entity.entity_id, unique_id))
    devices = dr.async_get(hass)
    legacy = DOMAIN, f"ezviz:{entry.data[CONF_ALIAS]}"
    device = devices.async_get_device_by_identifier(legacy, entry.entry_id)
    if device is not None:
        if device.config_entries == {entry.entry_id}:
            devices.async_update_device(
                device.id,
                new_identifiers=(device.identifiers - {legacy}) | {device_identifier(entry)},
            )
        else:
            # The old device may have merged aliases from distinct bridges. Split
            # this entry alone; never delete the shared device or other entities.
            replacement = devices.async_get_or_create(
                config_entry_id=entry.entry_id, **device_info(entry)
            )
            devices.async_update_device(
                replacement.id, name_by_user=device.name_by_user, area_id=device.area_id
            )
            for entity in list(registry.entities.values()):
                if entity.config_entry_id == entry.entry_id and entity.device_id == device.id:
                    registry.async_update_entity(entity.entity_id, device_id=replacement.id)
            devices.async_update_device(device.id, remove_config_entry_id=entry.entry_id)
    for entity_id, unique_id in changes:
        registry.async_update_entity(entity_id, new_unique_id=unique_id)
