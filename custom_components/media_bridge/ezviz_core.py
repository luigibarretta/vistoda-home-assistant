"""Home Assistant's native EZVIZ integration, seen only through registries and states.

A delegated entry never touches the official integration's runtime objects: it
finds the bound camera's device in the device registry, its entities in the
entity registry, and reads their published states.
"""

from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import CONF_EZVIZ_DELEGATE_CONTROLS, CONF_PROVIDER, DOMAIN, PROVIDER_EZVIZ
from .ezviz_binding import CONF_EZVIZ_SOURCE_ID, valid_source_id

EZVIZ_DOMAIN = "ezviz"
# Entries still starting are not failures. Every other state (setup_retry while the
# native integration retries its cloud login, not_loaded during a reload) counts as
# unavailable, and the repair waits out the continuous-outage grace (repairs.py).
PENDING_STATES = {"loaded", "setup_in_progress"}
# The official camera entity is unavailable exactly while EZVIZ reports it offline.
UNAVAILABLE = "unavailable"


def delegated(entry) -> bool:
    """Return the user's explicit choice; standalone (False) is the default."""
    return bool((getattr(entry, "options", None) or {}).get(CONF_EZVIZ_DELEGATE_CONTROLS, False))


def bound_serial(entry) -> str | None:
    source = entry.data.get(CONF_EZVIZ_SOURCE_ID)
    return source.rsplit(":", 1)[0] if valid_source_id(source) else None


def _entry_state(native) -> str | None:
    return getattr(getattr(native, "state", None), "value", None)


def native_device(hass, entry):
    """Return (device, native entry) when one official entry registered the bound camera."""
    serial = bound_serial(entry)
    if serial is None:
        return None
    device = dr.async_get(hass).async_get_device(identifiers={(EZVIZ_DOMAIN, serial)})
    if device is None:
        return None
    natives = [
        native
        for native in map(hass.config_entries.async_get_entry, device.config_entries)
        if getattr(native, "domain", None) == EZVIZ_DOMAIN
    ]
    return (device, natives[0]) if len(natives) == 1 else None


def native_entities(hass, device, native) -> list:
    """Enabled entity-registry entries of the official integration for one device."""
    return [
        entity
        for entity in er.async_entries_for_device(er.async_get(hass), device.id)
        if entity.config_entry_id == native.entry_id
    ]


def _camera_id(hass, device, native) -> str | None:
    cameras = [
        entity.entity_id
        for entity in native_entities(hass, device, native)
        if entity.entity_id.startswith("camera.")
    ]
    return cameras[0] if len(cameras) == 1 else None


def native_camera(hass, entry):
    """Return the official camera entity's current state while its entry is loaded."""
    resolved = native_device(hass, entry)
    if resolved is None or _entry_state(resolved[1]) != "loaded":
        return None
    camera = _camera_id(hass, *resolved)
    return hass.states.get(camera) if camera else None


def native_controls_available(hass, entry) -> bool:
    """Return whether the official integration currently serves the bound camera."""
    return native_camera(hass, entry) is not None


def native_camera_online(hass, entry) -> bool | None:
    """Return the bound camera's state as the official camera entity publishes it."""
    state = native_camera(hass, entry)
    return None if state is None else state.state != UNAVAILABLE


def _served(hass, entry) -> bool:
    """Same test as native_controls_available, tolerating an entry still starting."""
    resolved = native_device(hass, entry)
    if resolved is None or _entry_state(resolved[1]) not in PENDING_STATES:
        return False
    return _entry_state(resolved[1]) != "loaded" or native_camera(hass, entry) is not None


def refresh_core_issue(hass, *, exclude_entry_id: str | None = None) -> None:
    """Raise one global repair only while a delegated entry lacks the native integration.

    Standalone entries (the default) use the Vistoda EZVIZ app's own login and
    never require Home Assistant's EZVIZ integration.
    """
    from .repairs import update_ezviz_core_issue

    if not getattr(hass, "is_running", True):
        return  # Native entries may still be queued during Home Assistant startup.
    unserved = any(
        entry.data.get(CONF_PROVIDER) == PROVIDER_EZVIZ
        and entry.entry_id != exclude_entry_id
        and getattr(entry, "disabled_by", None) is None
        and delegated(entry)
        and not _served(hass, entry)
        for entry in hass.config_entries.async_entries(DOMAIN)
    )
    update_ezviz_core_issue(hass, available=not unserved)
