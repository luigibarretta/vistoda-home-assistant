"""Charging binary sensor of EZVIZ cameras (Vistoda EZVIZ app 0.13+)."""

from custom_components.media_bridge.client_ezviz_controls import EzvizControls
from tests.test_ezviz_controls_runtime import stub


def test_charging_entity_only_when_the_app_reports_it(monkeypatch) -> None:
    _issues, controls = stub(monkeypatch)
    older_app = controls.EzvizControlsStatus(True, EzvizControls(battery_percent=100))
    newer_app = controls.EzvizControlsStatus(
        True,
        EzvizControls(battery_percent=100, battery_charging=False, battery_power_source="battery"),
    )
    assert controls.reports_battery(older_app) and not controls.reports_charging(older_app)
    assert controls.reports_charging(newer_app)
    assert controls.CHARGING_SUFFIX == "charging"
