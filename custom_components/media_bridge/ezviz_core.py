"""Read-only view of Home Assistant's native EZVIZ integration for one camera."""

from .const import CONF_EZVIZ_DELEGATE_CONTROLS, CONF_PROVIDER, DOMAIN, PROVIDER_EZVIZ
from .ezviz_binding import CONF_EZVIZ_SOURCE_ID, valid_source_id

EZVIZ_DOMAIN = "ezviz"
# pyezvizapi reports deviceInfos.status; HA core treats 2 as offline.
STATUS_ONLINE = 1
STATUS_OFFLINE = 2
# Entries still starting are not failures; every other non-loaded state is.
PENDING_STATES = {"loaded", "setup_in_progress"}
# RTSP-only native entries: no cloud coordinator, settings, arming or connectivity.
CAMERA_ACCOUNT = "CAMERA_ACCOUNT"


def delegated(entry) -> bool:
    """Return the user's explicit choice; standalone (False) is the default."""
    return bool((getattr(entry, "options", None) or {}).get(CONF_EZVIZ_DELEGATE_CONTROLS, False))


def _cloud_entry(native) -> bool:
    return (getattr(native, "data", None) or {}).get("type") != CAMERA_ACCOUNT


def native_camera(hass, entry):
    """Return (coordinator, serial) only when exactly one native entry owns the serial."""
    source = entry.data.get(CONF_EZVIZ_SOURCE_ID)
    if not valid_source_id(source):
        return None
    serial = source.rsplit(":", 1)[0]
    matches = []
    for native in hass.config_entries.async_entries(EZVIZ_DOMAIN):
        coordinator = getattr(native, "runtime_data", None)
        data = getattr(coordinator, "data", None)
        if _cloud_entry(native) and isinstance(data, dict) and isinstance(data.get(serial), dict):
            matches.append((coordinator, serial))
    return matches[0] if len(matches) == 1 else None


def native_controls_available(hass, entry) -> bool:
    """Return whether a healthy native cloud coordinator owns the bound serial."""
    resolved = native_camera(hass, entry)
    return resolved is not None and bool(getattr(resolved[0], "last_update_success", False))


def camera_online(data) -> bool | None:
    """Map the native status code to online/offline; unknown codes stay unknown."""
    status = data.get("status") if isinstance(data, dict) else None
    if isinstance(status, str) and status.isdecimal():
        status = int(status)
    if isinstance(status, bool) or not isinstance(status, int):
        return None
    if status == STATUS_ONLINE:
        return True
    return False if status == STATUS_OFFLINE else None


def native_camera_online(hass, entry) -> bool | None:
    """Return the bound camera's state from a healthy native coordinator."""
    resolved = native_camera(hass, entry)
    if resolved is None:
        return None
    coordinator, serial = resolved
    if not getattr(coordinator, "last_update_success", False):
        return None
    return camera_online(coordinator.data.get(serial))


def core_available(hass) -> bool:
    """Return whether a native EZVIZ cloud entry is loaded or still starting."""
    return any(
        getattr(getattr(native, "state", None), "value", None) in PENDING_STATES
        and _cloud_entry(native)
        for native in hass.config_entries.async_entries(EZVIZ_DOMAIN)
    )


def refresh_core_issue(hass, *, exclude_entry_id: str | None = None) -> None:
    """Raise one global repair only while a delegated entry lacks the native integration.

    Standalone entries (the default) use the Vistoda EZVIZ app's own login and
    never require Home Assistant's EZVIZ integration.
    """
    from .repairs import update_ezviz_core_issue

    if not getattr(hass, "is_running", True):
        return  # Native entries may still be queued during Home Assistant startup.
    needed = any(
        entry.data.get(CONF_PROVIDER) == PROVIDER_EZVIZ
        and entry.entry_id != exclude_entry_id
        and getattr(entry, "disabled_by", None) is None
        and delegated(entry)
        for entry in hass.config_entries.async_entries(DOMAIN)
    )
    update_ezviz_core_issue(hass, available=not needed or core_available(hass))
