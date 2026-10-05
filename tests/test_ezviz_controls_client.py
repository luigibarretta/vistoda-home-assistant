"""Vistoda EZVIZ 0.10 controls, PTZ and account defence client contracts."""

import pytest

from custom_components.media_bridge.client import BridgeClient
from custom_components.media_bridge.client_ezviz_controls import (
    EzvizControlConflictError,
    EzvizControls,
    EzvizControlUnconfirmedError,
    EzvizRange,
    parse_controls,
    parse_defence_mode,
)
from custom_components.media_bridge.client_ezviz_media import EzvizFeatureUnsupportedError
from custom_components.media_bridge.errors import (
    CannotConnectError,
    InvalidBridgeAuthError,
    ReauthRequiredError,
)
from tests.test_client import FakeResponse, FakeSession, response

FULL = {
    "online": True,
    "defence_enabled": False,
    "alarm_schedule_enabled": True,
    "detection_mode": "pir",
    "sensitivity": {"value": 3, "min": 1, "max": 6},
    "switches": {"privacy": False, "wdr": True, "Bad Name": True, "logo": "yes"},
    "ptz": True,
    "battery": {"percent": 87, "work_mode": "power_saving"},
    "firmware": {"version": " V5.3.0 build 240101 ", "update_available": False},
}


def client(*responses) -> tuple[BridgeClient, FakeSession]:
    session = FakeSession(list(responses))
    return BridgeClient(session, "http://ezviz.local:8787", "x" * 32), session


def test_controls_document_maps_every_field_and_tolerates_garbage() -> None:
    assert parse_controls(FULL) == EzvizControls(
        online=True,
        defence_enabled=False,
        alarm_schedule_enabled=True,
        detection_mode="pir",
        sensitivity=EzvizRange(3, 1, 6),
        switches=(("privacy", False), ("wdr", True)),
        ptz=True,
        battery_percent=87,
        battery_work_mode="power_saving",
        firmware_version="V5.3.0 build 240101",
        firmware_update_available=False,
    )
    garbage = {
        "online": 1,
        "detection_mode": "vehicle",
        "sensitivity": {"value": 9, "min": 1, "max": 6},
        "switches": ["privacy"],
        "ptz": "true",
        "battery": {"percent": 101, "work_mode": "Power Saving"},
        "firmware": {"version": "\x00", "update_available": "no"},
    }
    assert parse_controls(garbage) == EzvizControls()
    assert parse_controls({"sensitivity": {"value": 2, "min": 5, "max": 1}}).sensitivity is None
    assert parse_controls({"sensitivity": {"value": True, "min": 0, "max": 1}}).sensitivity is None
    with pytest.raises(CannotConnectError):
        parse_controls([])
    assert parse_defence_mode({"mode": "sleep"}) == "sleep"
    assert parse_defence_mode({"mode": None}) is None
    assert parse_defence_mode({"mode": "party"}) is None


async def test_controls_routes_are_authenticated_and_404_means_older_app() -> None:
    api, session = client(
        response(200, FULL),
        FakeResponse(404, b'{"error":"not_found"}'),
        FakeResponse(401, b""),
        FakeResponse(403, b'{"error":"reauth_required"}'),
    )
    assert (await api.ezviz_controls("front door")).ptz is True
    method, url, options = session.requests[0]
    assert (method, url) == ("GET", "http://ezviz.local:8787/v1/cameras/front%20door/controls")
    assert options["headers"]["Authorization"] == f"Bearer {'x' * 32}"
    with pytest.raises(EzvizFeatureUnsupportedError):
        await api.ezviz_controls("front door")
    with pytest.raises(InvalidBridgeAuthError):
        await api.ezviz_controls("front door")
    with pytest.raises(ReauthRequiredError):
        await api.ezviz_controls("front door")


async def test_control_writes_map_conflict_and_unconfirmed() -> None:
    api, session = client(
        response(200, {**FULL, "defence_enabled": True}),
        FakeResponse(409, b'{"error":"conflict"}'),
        FakeResponse(502, b'{"error":"unconfirmed"}'),
        FakeResponse(502, b'{"error":"upstream"}'),
    )
    confirmed = await api.ezviz_set_control("cam", "defence_enabled", True, False)
    assert confirmed.defence_enabled is True
    method, url, options = session.requests[0]
    assert (method, url.rsplit("/", 2)[-2:]) == ("PUT", ["cam", "controls"])
    assert options["json"] == {"key": "defence_enabled", "value": True, "expected_value": False}
    with pytest.raises(EzvizControlConflictError):
        await api.ezviz_set_control("cam", "switch.privacy", True, False)
    with pytest.raises(EzvizControlUnconfirmedError):
        await api.ezviz_set_control("cam", "sensitivity", 4, 3)
    with pytest.raises(CannotConnectError) as error:
        await api.ezviz_set_control("cam", "sensitivity", 4, 3)
    assert not isinstance(error.value, EzvizControlUnconfirmedError)


async def test_ptz_and_account_defence_routes() -> None:
    api, session = client(
        FakeResponse(204, b""),
        FakeResponse(409, b'{"error":"unsupported"}'),
        response(200, {"mode": "away"}),
        response(200, {"mode": "sleep"}),
        FakeResponse(404, b""),
    )
    await api.ezviz_ptz("cam", "left")
    assert session.requests[0][0] == "POST"
    assert session.requests[0][1].endswith("/v1/cameras/cam/ptz")
    assert session.requests[0][2]["json"] == {"direction": "left"}
    with pytest.raises(EzvizControlConflictError):
        await api.ezviz_ptz("cam", "up")
    with pytest.raises(ValueError):
        await api.ezviz_ptz("cam", "zoom")
    assert await api.ezviz_account_defence() == "away"
    assert await api.ezviz_set_account_defence("sleep", "away") == "sleep"
    method, url, options = session.requests[3]
    assert (method, url) == ("PUT", "http://ezviz.local:8787/v1/account/defence")
    assert options["json"] == {"mode": "sleep", "expected_mode": "away"}
    with pytest.raises(EzvizFeatureUnsupportedError):
        await api.ezviz_account_defence()
    with pytest.raises(ValueError):
        await api.ezviz_set_account_defence("disarmed", "home")
    assert len(session.requests) == 5
