"""Read-only view of Home Assistant's native EZVIZ integration for one camera."""

from .const import CONF_PROVIDER, DOMAIN, PROVIDER_EZVIZ
from .ezviz_binding import CONF_EZVIZ_SOURCE_ID, valid_source_id

EZVIZ_DOMAIN = "ezviz"
# pyezvizapi reports deviceInfos.status; HA core treats 2 as offline.
STATUS_ONLINE = 1
STATUS_OFFLINE = 2
# Entries still starting are not failures; every other non-loaded state is.
PENDING_STATES = {"loaded", "setup_in_progress"}


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
        if isinstance(data, dict) and isinstance(data.get(serial), dict):
            matches.append((coordinator, serial))
    return matches[0] if len(matches) == 1 else None


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
    # RTSP-only "CAMERA_ACCOUNT" entries have no cloud coordinator, so they
    # cannot provide settings, arming or connectivity.
    return any(
        getattr(getattr(native, "state", None), "value", None) in PENDING_STATES
        and (getattr(native, "data", None) or {}).get("type") != "CAMERA_ACCOUNT"
        for native in hass.config_entries.async_entries(EZVIZ_DOMAIN)
    )


def refresh_core_issue(hass, *, exclude_entry_id: str | None = None) -> None:
    """Raise one global repair while any Vistoda EZVIZ entry depends on the native one."""
    from .repairs import update_ezviz_core_issue

    if not getattr(hass, "is_running", True):
        return  # Native entries may still be queued during Home Assistant startup.
    needed = any(
        entry.data.get(CONF_PROVIDER) == PROVIDER_EZVIZ
        and entry.entry_id != exclude_entry_id
        and getattr(entry, "disabled_by", None) is None
        for entry in hass.config_entries.async_entries(DOMAIN)
    )
    update_ezviz_core_issue(hass, available=not needed or core_available(hass))
