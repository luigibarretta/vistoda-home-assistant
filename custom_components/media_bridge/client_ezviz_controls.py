"""Vistoda EZVIZ 0.10 camera controls, PTZ and account defence contracts."""

import json
import re
from dataclasses import dataclass
from urllib.parse import quote

from .client_ezviz_media import EzvizFeatureUnsupportedError
from .client_helpers import error_code
from .errors import BridgeError, CannotConnectError

CONTROLS_LIMIT = 32 * 1024
DETECTION_MODES = ("human_shape", "image_change", "pir")
DEFENCE_MODES = ("home", "away", "sleep")
PTZ_DIRECTIONS = ("up", "down", "left", "right")
NAME = re.compile(r"[a-z][a-z0-9_]{0,47}")
MAX_SWITCHES = 64
SENSITIVITY_BOUND = 1000
FIRMWARE_LENGTH = 64


class EzvizControlConflictError(BridgeError):
    """HTTP 409: the value changed upstream, or the command is unsupported."""


class EzvizControlUnconfirmedError(BridgeError):
    """HTTP 502 "unconfirmed": the app could not read the write back and rolled it back."""


@dataclass(frozen=True, slots=True)
class EzvizRange:
    value: int
    minimum: int
    maximum: int


@dataclass(frozen=True, slots=True)
class EzvizControls:
    """Every field is optional: None means the app does not report it."""

    online: bool | None = None
    defence_enabled: bool | None = None
    alarm_schedule_enabled: bool | None = None
    detection_mode: str | None = None
    sensitivity: EzvizRange | None = None
    switches: tuple[tuple[str, bool], ...] = ()
    ptz: bool = False
    battery_percent: int | None = None
    battery_work_mode: str | None = None
    firmware_version: str | None = None
    firmware_update_available: bool | None = None


def _flag(value) -> bool | None:
    return value if isinstance(value, bool) else None


def _number(value, low: int, high: int) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        return None
    return value


def _sensitivity(raw) -> EzvizRange | None:
    if not isinstance(raw, dict):
        return None
    bound = SENSITIVITY_BOUND
    low, high = _number(raw.get("min"), -bound, bound), _number(raw.get("max"), -bound, bound)
    if low is None or high is None or low >= high:
        return None
    value = _number(raw.get("value"), low, high)
    return None if value is None else EzvizRange(value, low, high)


def _switches(raw) -> tuple[tuple[str, bool], ...]:
    if not isinstance(raw, dict):
        return ()
    valid = [
        (name, value)
        for name, value in raw.items()
        if isinstance(name, str) and NAME.fullmatch(name) and isinstance(value, bool)
    ]
    return tuple(sorted(valid)[:MAX_SWITCHES])


def _firmware_version(raw) -> str | None:
    value = raw.get("version")
    if not isinstance(value, str) or not value.isprintable():
        return None
    value = value.strip()
    return value[:FIRMWARE_LENGTH] or None


def parse_controls(payload) -> EzvizControls:
    """Unknown or malformed fields degrade to None instead of failing the document."""
    if not isinstance(payload, dict):
        raise CannotConnectError
    mode = payload.get("detection_mode")
    battery = payload.get("battery") if isinstance(payload.get("battery"), dict) else {}
    work_mode = battery.get("work_mode")
    firmware = payload.get("firmware") if isinstance(payload.get("firmware"), dict) else {}
    return EzvizControls(
        online=_flag(payload.get("online")),
        defence_enabled=_flag(payload.get("defence_enabled")),
        alarm_schedule_enabled=_flag(payload.get("alarm_schedule_enabled")),
        detection_mode=mode if mode in DETECTION_MODES else None,
        sensitivity=_sensitivity(payload.get("sensitivity")),
        switches=_switches(payload.get("switches")),
        ptz=payload.get("ptz") is True,
        battery_percent=_number(battery.get("percent"), 0, 100),
        battery_work_mode=work_mode
        if isinstance(work_mode, str) and NAME.fullmatch(work_mode)
        else None,
        firmware_version=_firmware_version(firmware),
        firmware_update_available=_flag(firmware.get("update_available")),
    )


def parse_defence_mode(payload) -> str | None:
    if not isinstance(payload, dict):
        raise CannotConnectError
    mode = payload.get("mode")
    return mode if mode in DEFENCE_MODES else None


class EzvizControlsClientMixin:
    """A 404 on any route below means the app predates Vistoda EZVIZ 0.10."""

    async def _ezviz_control(self, method: str, path: str, **kwargs):
        response = await self._request(method, path, **kwargs)
        async with response:
            body = await self._bounded(response, CONTROLS_LIMIT)
            status = response.status
        if status == 404:
            raise EzvizFeatureUnsupportedError
        if status == 409:
            raise EzvizControlConflictError
        if status == 502 and error_code(body) == "unconfirmed":
            raise EzvizControlUnconfirmedError
        if status == 204:
            return None
        if status < 200 or status >= 300:
            self._raise_status(status, body)
        try:
            return json.loads(body)
        except (ValueError, TypeError) as error:
            raise CannotConnectError from error

    async def ezviz_controls(self, alias: str) -> EzvizControls:
        path = f"/v1/cameras/{quote(alias, safe='')}/controls"
        return parse_controls(await self._ezviz_control("GET", path))

    async def ezviz_set_control(self, alias: str, key: str, value, expected_value):
        """Write one control; the app compares, writes and reads back before answering."""
        path = f"/v1/cameras/{quote(alias, safe='')}/controls"
        payload = {"key": key, "value": value, "expected_value": expected_value}
        return parse_controls(await self._ezviz_control("PUT", path, json=payload))

    async def ezviz_ptz(self, alias: str, direction: str) -> None:
        if direction not in PTZ_DIRECTIONS:
            raise ValueError("unsupported PTZ direction")
        path = f"/v1/cameras/{quote(alias, safe='')}/ptz"
        await self._ezviz_control("POST", path, json={"direction": direction})

    async def ezviz_account_defence(self) -> str | None:
        return parse_defence_mode(await self._ezviz_control("GET", "/v1/account/defence"))

    async def ezviz_set_account_defence(self, mode: str, expected_mode: str | None):
        """Return the confirmed mode, or None when the app answered without a body."""
        if mode not in DEFENCE_MODES:
            raise ValueError("unsupported defence mode")
        payload = {"mode": mode, "expected_mode": expected_mode}
        result = await self._ezviz_control("PUT", "/v1/account/defence", json=payload)
        return None if result is None else parse_defence_mode(result)
