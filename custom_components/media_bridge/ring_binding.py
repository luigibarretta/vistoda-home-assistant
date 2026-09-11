"""Persistent physical-device binding and non-destructive Ring registry migration."""

from .const import CONF_ALIAS, DOMAIN

CONF_RING_DEVICE_ID = "ring_device_id"
CONF_RING_OFFICIAL_BINDING = "ring_official_binding"


def valid_device_id(value) -> bool:
    return isinstance(value, str) and value.isascii() and value.isdecimal() and len(value) <= 32


def device_identifier(entry) -> tuple[str, str]:
    """Aliases belong to a provider instance; HA identities belong to an entry."""
    return DOMAIN, f"ring:{entry.entry_id}"


def entity_prefix(entry) -> str:
    return f"ring-{entry.entry_id}-"


def verified_device_id(entry, status) -> str | None:
    """A provider alias must still resolve to the enrolled physical device."""
    expected = entry.data.get(CONF_RING_DEVICE_ID)
    actual = getattr(status, "device_id", None)
    return expected if expected and actual == expected else None


async def async_verify_native(hass, entry_id, client, alias) -> str:
    """Refresh the physical target before opening an audio or control boundary."""
    from .errors import CannotConnectError

    entry = hass.config_entries.async_get_entry(entry_id)
    status = await client.ring_status(alias)
    if entry is None or verified_device_id(entry, status) is None or not status.online:
        raise CannotConnectError
    return entry.data[CONF_RING_DEVICE_ID]


def async_bind_native(hass, entry, status) -> bool:
    """Pin initial native identity; never silently accept an alias retarget."""
    device_id = getattr(status, "device_id", None)
    if not isinstance(device_id, str) or not device_id.isascii() or not device_id.isdecimal():
        return False
    if entry.data.get(CONF_RING_DEVICE_ID) is None:
        hass.config_entries.async_update_entry(
            entry, data={**entry.data, CONF_RING_DEVICE_ID: device_id}
        )
    return verified_device_id(entry, status) is not None


def async_migrate_registry(hass, entry) -> None:
    """Preserve entity IDs, user names and automation references during namespacing."""
    from homeassistant.helpers import device_registry as dr
    from homeassistant.helpers import entity_registry as er

    entities = er.async_get(hass)
    legacy_prefix = f"ring-{entry.data[CONF_ALIAS]}-"
    for entity in list(entities.entities.values()):
        if entity.config_entry_id == entry.entry_id and entity.unique_id.startswith(legacy_prefix):
            entities.async_update_entity(
                entity.entity_id,
                new_unique_id=entity_prefix(entry) + entity.unique_id.removeprefix(legacy_prefix),
            )
    devices = dr.async_get(hass)
    legacy = (DOMAIN, f"ring:{entry.data[CONF_ALIAS]}")
    device = devices.async_get_device_by_identifier(legacy, entry.entry_id)
    if device is None:
        return
    # Older duplicate aliases could share a device. Split only the current entry;
    # the legacy device and every other entry remain intact.
    if device.config_entries == {entry.entry_id}:
        devices.async_update_device(
            device.id, new_identifiers=(device.identifiers - {legacy}) | {device_identifier(entry)}
        )
    else:
        replacement = devices.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={device_identifier(entry)},
            name=device.name_by_user or device.name,
            manufacturer="Vistoda",
            model="Ring Intercom enhanced bridge",
        )
        for entity in list(entities.entities.values()):
            if entity.config_entry_id == entry.entry_id and entity.device_id == device.id:
                entities.async_update_entity(entity.entity_id, device_id=replacement.id)
        devices.async_update_device(device.id, remove_config_entry_id=entry.entry_id)
