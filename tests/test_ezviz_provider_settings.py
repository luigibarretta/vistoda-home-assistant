"""Typed tests for private EZVIZ settings exposed through Vistoda."""

from pathlib import Path

from custom_components.media_bridge.ezviz_provider_settings import (
    current_value,
    provider_value,
    settings_from_data,
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
