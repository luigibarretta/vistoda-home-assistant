"""Typed tests for private EZVIZ settings exposed through Vistoda."""

from pathlib import Path

import pytest

from custom_components.media_bridge.ezviz_provider_settings import (
    current_value,
    provider_value,
    settings_from_data,
    writable,
)


def test_only_current_unambiguous_provider_settings_are_exposed() -> None:
    settings = settings_from_data(
        {
            "battery_camera_work_mode": 4,
            "push_notify_alarm": True,
            "push_notify_call": False,
            "offline_notify": 1,
            "switches": {200: 1, "604": 0, 617: True, 702: False},
        }
    )
    assert {item["key"] for item in settings} == {
        "battery_work_mode",
        "receive_device_message",
        "answer_doorbell_call",
        "offline_notification",
        "human_detection",
        "wide_dynamic_range",
        "distortion_correction",
        "logo_watermark",
    }
    assert (
        current_value({"battery_camera_work_mode": 4}, "battery_work_mode") == "user_customization"
    )


def test_provider_calls_are_typed_and_notification_inversion_is_explicit() -> None:
    assert provider_value("receive_device_message", True) == ("do_not_disturb", (0,))
    assert provider_value("battery_work_mode", "power_saving") == (
        "set_battery_camera_work_mode",
        (0,),
    )
    assert provider_value("wide_dynamic_range", True) == ("switch_status", (604, 1))


def test_private_settings_boundary_is_admin_gated_and_verified() -> None:
    component = Path("custom_components/media_bridge")
    websocket = (component / "ezviz_settings_websocket.py").read_text(encoding="utf-8")
    frontend = (component / "frontend" / "ezviz-settings.js").read_text(encoding="utf-8")
    assert "if not connection.user.is_admin" in websocket
    assert "expected_value" in websocket and "read-after-write mismatch" in websocket
    assert "media_bridge/ezviz/settings/info" in frontend
    assert "media_bridge/ezviz/settings/set" in frontend
    assert "Conferma modifiche EZVIZ" in frontend


def test_per_camera_arming_and_detection_mode_follow_native_data() -> None:
    data = {
        "alarm_notify": True,
        "alarm_schedules_enabled": False,
        "Alarm_DetectHumanCar": "5",
        "supportExt": {"1": "1"},
    }
    settings = {item["key"]: item for item in settings_from_data(data)}
    assert settings["camera_defence"] == {
        "key": "camera_defence",
        "group": "arming",
        "kind": "boolean",
        "value": True,
    }
    assert settings["alarm_schedule"]["kind"] == "status"
    assert settings["alarm_schedule"]["value"] is False
    assert settings["detection_mode"]["value"] == "pir"
    assert settings["detection_mode"]["options"] == ["human_shape", "image_change", "pir"]
    # Explicitly unsupported defence, unknown detection types and missing flags stay hidden.
    hidden = settings_from_data(
        {"alarm_notify": True, "supportExt": {"1": "0"}, "Alarm_DetectHumanCar": 9}
    )
    assert hidden == []
    assert settings_from_data({"alarm_notify": None, "alarm_schedules_enabled": None}) == []


def test_arming_writes_map_to_pinned_pyezvizapi_calls_and_schedule_is_read_only() -> None:
    assert provider_value("camera_defence", True) == ("set_camera_defence", (1,))
    assert provider_value("camera_defence", False) == ("set_camera_defence", (0,))
    assert provider_value("detection_mode", "image_change") == ("set_detection_mode", (3,))
    assert writable("camera_defence") and writable("detection_mode")
    assert writable("human_detection") and writable("battery_work_mode")
    assert not writable("alarm_schedule") and not writable("unknown")
    for key, value in (
        ("alarm_schedule", True),
        ("camera_defence", "1"),
        ("detection_mode", "vehicle"),
    ):
        with pytest.raises(ValueError):
            provider_value(key, value)
