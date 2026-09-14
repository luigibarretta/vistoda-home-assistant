"""Typed EZVIZ cloud settings omitted by native Home Assistant entities."""

from typing import Any

WORK_MODES = {
    0: "power_saving",
    1: "high_performance",
    3: "super_power_saving",
    4: "user_customization",
}
SWITCH_SETTINGS = {
    200: ("human_detection", "detection"),
    604: ("wide_dynamic_range", "image"),
    617: ("distortion_correction", "image"),
    702: ("logo_watermark", "image"),
}


def _boolean(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value)
    if isinstance(value, str) and value.lower() in {"0", "1", "true", "false"}:
        return value.lower() in {"1", "true"}
    return None


def settings_from_data(data: dict) -> list[dict]:
    """Return only settings whose current provider value is unambiguous."""
    result = []
    try:
        work_mode = int(data.get("battery_camera_work_mode"))
    except (TypeError, ValueError):
        work_mode = None
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
    return result


def current_value(data: dict, key: str) -> Any:
    """Resolve one setting from freshly polled provider data."""
    return next((item["value"] for item in settings_from_data(data) if item["key"] == key), None)


def provider_value(key: str, value: Any) -> tuple[str, tuple]:
    """Map one validated UI value to an existing pyezvizapi call."""
    if key == "battery_work_mode" and value in WORK_MODES.values():
        raw = next(raw for raw, label in WORK_MODES.items() if label == value)
        return "set_battery_camera_work_mode", (raw,)
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
