"""Map Vistoda EZVIZ app controls onto the panel's existing setting keys.

The panel keeps one vocabulary for both sources: native-only keys stay as they
were, and app controls reuse them wherever the meaning is identical. Only
values the app reports are listed, so unknown items are never shown.
"""

from typing import Any

from .client_ezviz_controls import DETECTION_MODES, EzvizControls

# App switch name -> (panel key, panel group). Unknown names keep "switch.<name>".
SWITCHES = {
    "human_detection": ("human_detection", "detection"),
    "wdr": ("wide_dynamic_range", "image"),
    "distortion_correction": ("distortion_correction", "image"),
    "logo": ("logo_watermark", "image"),
    "infrared_light": ("infrared_light", "image"),
    "status_light": ("status_light", "light"),
    "privacy": ("privacy_mode", "privacy"),
    "sleep": ("sleep_mode", "privacy"),
}
# Panel key -> app control key for the non-switch writable controls.
DIRECT = {
    "camera_defence": "defence_enabled",
    "detection_mode": "detection_mode",
    "detection_sensitivity": "sensitivity",
}
SWITCH_PREFIX = "switch."


def _switch_key(name: str) -> tuple[str, str]:
    return SWITCHES.get(name, (f"{SWITCH_PREFIX}{name}", "other"))


def _info(key: str, group: str, value, **extra) -> dict:
    return {"key": key, "group": group, "kind": "info", "value": value, **extra}


def settings_from_controls(controls: EzvizControls) -> list[dict]:
    """Return the panel settings list for one camera, in display order."""
    result = []
    if controls.defence_enabled is not None:
        result.append(
            {
                "key": "camera_defence",
                "group": "arming",
                "kind": "boolean",
                "value": controls.defence_enabled,
            }
        )
    if controls.alarm_schedule_enabled is not None:
        value = controls.alarm_schedule_enabled
        result.append(
            {"key": "alarm_schedule", "group": "arming", "kind": "status", "value": value}
        )
    if controls.battery_percent is not None:
        result.append(_info("battery_level", "battery", controls.battery_percent, unit="%"))
    if controls.battery_work_mode is not None:
        result.append(_info("battery_work_mode", "battery", controls.battery_work_mode))
    if controls.detection_mode is not None:
        result.append(
            {
                "key": "detection_mode",
                "group": "detection",
                "kind": "select",
                "value": controls.detection_mode,
                "options": list(DETECTION_MODES),
            }
        )
    sensitivity = controls.sensitivity
    if sensitivity is not None:
        result.append(
            {
                "key": "detection_sensitivity",
                "group": "detection",
                "kind": "number",
                "value": sensitivity.value,
                "min": sensitivity.minimum,
                "max": sensitivity.maximum,
            }
        )
    for name, value in controls.switches:
        key, group = _switch_key(name)
        result.append({"key": key, "group": group, "kind": "boolean", "value": value})
    if controls.firmware_version is not None:
        result.append(_info("firmware_version", "device", controls.firmware_version))
    if controls.firmware_update_available is not None:
        result.append(_info("firmware_update", "device", controls.firmware_update_available))
    return result


def control_key(key: str, controls: EzvizControls) -> str | None:
    """Return the app key for a writable panel key the app currently reports."""
    reported = {item["key"]: item for item in settings_from_controls(controls)}
    item = reported.get(key)
    if item is None or item["kind"] not in {"boolean", "select", "number"}:
        return None
    if key in DIRECT:
        return DIRECT[key]
    name = next((name for name, (mapped, _group) in SWITCHES.items() if mapped == key), None)
    if name is None and key.startswith(SWITCH_PREFIX):
        name = key.removeprefix(SWITCH_PREFIX)
    return f"{SWITCH_PREFIX}{name}" if name else None


def valid_value(key: str, value: Any, controls: EzvizControls) -> bool:
    """Reject values the reported control cannot take before any app call."""
    item = next((item for item in settings_from_controls(controls) if item["key"] == key), None)
    if item is None:
        return False
    if item["kind"] == "boolean":
        return isinstance(value, bool)
    if item["kind"] == "select":
        return value in item["options"]
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and item["min"] <= value <= item["max"]
    )
