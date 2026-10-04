"""Typed EZVIZ cloud settings omitted by native Home Assistant entities."""

from typing import Any

WORK_MODES = {
    0: "power_saving",
    1: "high_performance",
    3: "super_power_saving",
    4: "user_customization",
}
# Alarm_DetectHumanCar "type" values understood by pyezvizapi 1.0.0.7
# (IntelligentDetectionMode); unknown device values are never shown.
DETECTION_MODES = {1: "human_shape", 3: "image_change", 5: "pir"}
SWITCH_SETTINGS = {
    200: ("human_detection", "detection"),
    604: ("wide_dynamic_range", "image"),
    617: ("distortion_correction", "image"),
    702: ("logo_watermark", "image"),
}
# supportExt capability "SupportDefence"; "0" explicitly means no per-camera arming.
SUPPORT_DEFENCE = "1"
READ_ONLY = frozenset({"alarm_schedule"})


def _boolean(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value)
    if isinstance(value, str) and value.lower() in {"0", "1", "true", "false"}:
        return value.lower() in {"1", "true"}
    return None


def _integer(value: Any) -> int | None:
    try:
        return None if isinstance(value, bool) else int(value)
    except (TypeError, ValueError):
        return None


def _arming(data: dict) -> list[dict]:
    """Per-camera defence (STATUS.globalStatus) and the read-only schedule flag."""
    result = []
    support = data.get("supportExt") if isinstance(data.get("supportExt"), dict) else {}
    defence = data.get("alarm_notify")
    if isinstance(defence, bool) and support.get(SUPPORT_DEFENCE) != "0":
        result.append(
            {"key": "camera_defence", "group": "arming", "kind": "boolean", "value": defence}
        )
    schedule = data.get("alarm_schedules_enabled")
    if isinstance(schedule, bool):
        result.append(
            {"key": "alarm_schedule", "group": "arming", "kind": "status", "value": schedule}
        )
    return result


def settings_from_data(data: dict) -> list[dict]:
    """Return only settings whose current provider value is unambiguous."""
    result = _arming(data)
    work_mode = _integer(data.get("battery_camera_work_mode"))
    if work_mode in WORK_MODES:
        result.append(
            {
                "key": "battery_work_mode",
                "group": "battery",
                "kind": "select",
                "value": WORK_MODES[work_mode],
                "options": list(WORK_MODES.values()),
            }
        )
    for key, field in (
        ("receive_device_message", "push_notify_alarm"),
        ("answer_doorbell_call", "push_notify_call"),
        ("offline_notification", "offline_notify"),
    ):
        value = _boolean(data.get(field))
        if value is not None:
            result.append({"key": key, "group": "notifications", "kind": "boolean", "value": value})
    switches = data.get("switches") if isinstance(data.get("switches"), dict) else {}
    for switch_type, (key, group) in SWITCH_SETTINGS.items():
        value = _boolean(switches.get(switch_type, switches.get(str(switch_type))))
        if value is not None:
            result.append({"key": key, "group": group, "kind": "boolean", "value": value})
    detection = _integer(data.get("Alarm_DetectHumanCar"))
    if detection in DETECTION_MODES:
        result.append(
            {
                "key": "detection_mode",
                "group": "detection",
                "kind": "select",
                "value": DETECTION_MODES[detection],
                "options": list(DETECTION_MODES.values()),
            }
        )
    return result


def current_value(data: dict, key: str) -> Any:
    """Resolve one setting from freshly polled provider data."""
    return next((item["value"] for item in settings_from_data(data) if item["key"] == key), None)


def writable(key: str) -> bool:
    """Return whether a key maps to a pyezvizapi write call at all."""
    known = {"battery_work_mode", "receive_device_message", "answer_doorbell_call"}
    known |= {"offline_notification", "camera_defence", "detection_mode"}
    known |= {key for key, _group in SWITCH_SETTINGS.values()}
    return key in known and key not in READ_ONLY


def provider_value(key: str, value: Any) -> tuple[str, tuple]:
    """Map one validated UI value to an existing pyezvizapi 1.0.0.7 call."""
    if key == "battery_work_mode" and value in WORK_MODES.values():
        raw = next(raw for raw, label in WORK_MODES.items() if label == value)
        return "set_battery_camera_work_mode", (raw,)
    if key == "detection_mode" and value in DETECTION_MODES.values():
        raw = next(raw for raw, label in DETECTION_MODES.items() if label == value)
        return "set_detection_mode", (raw,)
    if key == "camera_defence" and isinstance(value, bool):
        # Same call HA core uses for camera.enable/disable_motion_detection.
        return "set_camera_defence", (int(value),)
    if key == "receive_device_message" and isinstance(value, bool):
        return "do_not_disturb", (int(not value),)
    if key == "answer_doorbell_call" and isinstance(value, bool):
        return "set_answer_call", (int(value),)
    if key == "offline_notification" and isinstance(value, bool):
        return "set_offline_notification", (int(value),)
    switch = next((number for number, item in SWITCH_SETTINGS.items() if item[0] == key), None)
    if switch is not None and isinstance(value, bool):
        return "switch_status", (switch, int(value))
    raise ValueError("Unsupported EZVIZ setting value")
