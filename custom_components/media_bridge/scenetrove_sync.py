"""SceneTrove cloud microSD sync schedule for a linked EZVIZ entry (ADR 0029).

SceneTrove owns the schedule and runs the sync. Vistoda only reads it and
changes `enabled` and `interval_minutes` through
`/api/devices/{device}/sd-sync`, with a SceneTrove token that holds just the
`devices:sd-sync` scope. The token never leaves Home Assistant's backend.
"""

import json
import re
from typing import Any
from urllib.parse import quote

from aiohttp import ClientError, ClientSession, ClientTimeout

from .const import CONF_SCENETROVE_DEVICE, CONF_SCENETROVE_TOKEN, CONF_SCENETROVE_URL

# Minutes the panel offers besides "off" (frontend/scenetrove-sync-model.js);
# SceneTrove itself accepts 15-1440 and owns the stored value.
INTERVALS = (60, 180, 360, 720, 1440)
TOKEN = re.compile(r"scenetrove_pat_[A-Za-z0-9_-]{32,128}")
RESULTS = ("ok", "camera_offline", "bridge_busy", "bridge_error", "unavailable")
STATUS_LIMIT = 16 * 1024
TIMEOUT = ClientTimeout(total=15, connect=5)


class SceneTroveSyncError(Exception):
    """A stable, user-presentable failure code."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def sync_target(options: dict) -> tuple[str, str, str] | None:
    """SceneTrove root, device folder and token, or None while not linked."""
    url = options.get(CONF_SCENETROVE_URL, "")
    device = options.get(CONF_SCENETROVE_DEVICE, "")
    token = options.get(CONF_SCENETROVE_TOKEN, "")
    return (url, device, token) if url and device and token else None


def valid_schedule(enabled: Any, interval: Any) -> bool:
    """Only booleans; "on" takes an offered interval, while "off" accepts any
    interval SceneTrove accepts, so turning off keeps a custom one unchanged."""
    if not isinstance(enabled, bool) or not valid_interval(interval):
        return False
    return interval in INTERVALS or not enabled


def _text(value: Any, limit: int = 64) -> str | None:
    return value if isinstance(value, str) and 0 < len(value) <= limit else None


def _count(value: Any) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0


def status_payload(raw: Any) -> dict:
    """The panel's view of SceneTrove's status: no free-text upstream messages."""
    if not isinstance(raw, dict) or not isinstance(raw.get("settings"), dict):
        raise SceneTroveSyncError("scenetrove_invalid_response")
    settings = raw["settings"]
    interval = settings.get("interval_minutes")
    if not isinstance(settings.get("enabled"), bool) or not valid_interval(interval):
        raise SceneTroveSyncError("scenetrove_invalid_response")
    last = raw.get("last") if isinstance(raw.get("last"), dict) else None
    return {
        "enabled": settings["enabled"],
        "interval_minutes": interval,
        "available": raw.get("available") is True,
        "running": raw.get("running") is True,
        "last": None
        if last is None
        else {
            "result": last.get("result") if last.get("result") in RESULTS else "bridge_error",
            "finished_at": _text(last.get("finished_at")),
            "imported": _count(last.get("imported")),
            "failed": _count(last.get("failed")) + _count(last.get("given_up")),
        },
        "last_success_at": _text(raw.get("last_success_at")),
        "next_run_at": _text(raw.get("next_run_at")),
    }


def valid_interval(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and 15 <= value <= 1440


class SceneTroveSyncClient:
    """Bounded client for the one SceneTrove route Vistoda uses."""

    def __init__(self, session: ClientSession, url: str, device: str, token: str) -> None:
        self._session = session
        self._url = f"{url}/api/devices/{quote(device, safe='')}/sd-sync"
        self._token = token

    async def status(self) -> dict:
        return status_payload(await self._call("GET"))

    async def set_schedule(self, enabled: bool, interval_minutes: int) -> dict:
        body = {"enabled": enabled, "interval_minutes": interval_minutes}
        try:
            raw = await self._call("PUT", json=body)
        except SceneTroveSyncError as error:
            if error.code != "scenetrove_unknown_device":
                raise
            # A SceneTrove older than ADR-0023 has no schedule route: its PUT
            # falls through to the whole-device handler and answers 404 for a
            # device whose GET still works. A failing GET keeps its own code.
            await self._call("GET")
            raise SceneTroveSyncError("scenetrove_unsupported_version") from error
        return status_payload(raw)

    async def _call(self, method: str, **kwargs: Any) -> Any:
        headers = {"Authorization": f"Bearer {self._token}"}
        try:
            # A redirect would resend the token elsewhere: it is an error instead.
            response = await self._session.request(
                method,
                self._url,
                headers=headers,
                timeout=TIMEOUT,
                allow_redirects=False,
                **kwargs,
            )
            async with response:
                body = await _bounded(response)
                status = response.status
        except (ClientError, TimeoutError) as error:
            raise SceneTroveSyncError("scenetrove_unreachable") from error
        if status != 200:
            raise SceneTroveSyncError(_status_code(status, body))
        try:
            return json.loads(body)
        except ValueError as error:
            raise SceneTroveSyncError("scenetrove_invalid_response") from error


async def _bounded(response: Any) -> bytes:
    if response.content_length is not None and response.content_length > STATUS_LIMIT:
        raise SceneTroveSyncError("scenetrove_invalid_response")
    body = bytearray()
    async for chunk in response.content.iter_chunked(4096):
        if len(body) + len(chunk) > STATUS_LIMIT:
            raise SceneTroveSyncError("scenetrove_invalid_response")
        body.extend(chunk)
    return bytes(body)


def _status_code(status: int, body: bytes) -> str:
    """Map SceneTrove answers to the panel's stable codes."""
    try:
        upstream = json.loads(body).get("error", "")
    except (ValueError, AttributeError):
        upstream = ""
    if 300 <= status < 400:
        return "scenetrove_redirected"
    if status in (401, 403):
        # 403 admin_required: the token's SceneTrove user is not an administrator.
        return "scenetrove_unauthorized"
    if status == 404:
        return "scenetrove_unknown_device"
    if status == 409 and upstream == "live_source_required":
        return "scenetrove_live_source_required"
    if status == 400:
        return "scenetrove_rejected"
    return "scenetrove_unavailable"


async def verify_sync_token(session: ClientSession, url: str, token: str) -> str | None:
    """None when the token is narrow enough to store, else an options error key.

    A `devices:sd-sync` token must be refused (403) by SceneTrove's device
    list; a 200 means it can read every device (too broad). Anything else
    cannot prove the token narrow, so it is not stored either (ADR 0029).
    """
    try:
        response = await session.request(
            "GET",
            f"{url}/api/devices",
            headers={"Authorization": f"Bearer {token}"},
            timeout=TIMEOUT,
            allow_redirects=False,
        )
        async with response:
            status = response.status
    except (ClientError, TimeoutError):
        return "scenetrove_token_unverified"
    if status == 403:
        return None
    if status == 200:
        return "scenetrove_token_too_broad"
    if status == 401:
        return "scenetrove_token_rejected"
    return "scenetrove_token_unverified"
