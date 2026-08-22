"""Pure URL and enrollment helpers for the bridge client."""

import json
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from .errors import CannotConnectError
from .models import Enrollment


def normalize_url(value: str) -> str:
    """Accept only credential-free HTTP(S) bridge roots."""
    parts = urlsplit(value.strip())
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise ValueError("bridge URL must be HTTP(S)")
    if (
        parts.username
        or parts.password
        or parts.query
        or parts.fragment
        or parts.path not in ("", "/")
    ):
        raise ValueError("bridge URL cannot contain credentials, path, query or fragment")
    return urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip("/"), "", ""))


def parse_enrollment(payload: dict[str, Any]) -> Enrollment:
    """Parse one bounded two-step enrollment transition."""
    try:
        result = Enrollment(
            enrollment_id=str(payload["enrollment_id"]),
            next_step=str(payload["next_step"]),
            expires_in=int(payload["expires_in"]),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise CannotConnectError from error
    if result.next_step not in ("otp", "complete") or not 0 <= result.expires_in <= 120:
        raise CannotConnectError
    return result


def error_code(body: bytes) -> str:
    """Extract only the stable bridge error code."""
    try:
        payload = json.loads(body)
    except (ValueError, TypeError):
        return ""
    return payload.get("error", "") if isinstance(payload, dict) else ""
