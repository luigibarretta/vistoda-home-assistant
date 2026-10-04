"""Optional, read-only Ring unlock settings reported by Vistoda Ring 0.16+."""

import re
from dataclasses import dataclass

from .ring_binding import entity_prefix

# Engines may add modes later: keep any short identifier, never free text.
MODE = re.compile(r"[A-Za-z0-9_-]{1,32}")
MAX_DURATION_SECONDS = 3600
RING_TO_OPEN = "ring_to_open"
UNLOCK_MODE_SUFFIX = "unlock-mode"


def unlock_mode_unique_id(entry) -> str:
    """Stable registry identity of the read-only unlock type sensor."""
    return f"{entity_prefix(entry)}{UNLOCK_MODE_SUFFIX}"


@dataclass(frozen=True, slots=True)
class RingUnlockSettings:
    """Unlock type and duration; every field is optional in the contract."""

    mode: str | None
    ring_to_open_enabled: bool | None
    duration_seconds: int | None

    @property
    def effective_mode(self) -> str | None:
        """Prefer the explicit mode; an older payload may only carry the flag."""
        if self.mode is not None:
            return self.mode
        return RING_TO_OPEN if self.ring_to_open_enabled is True else None


def parse_unlock_settings(value) -> RingUnlockSettings | None:
    """Tolerate missing keys and unknown modes; malformed data is simply unknown."""
    if not isinstance(value, dict):
        return None
    mode = value.get("mode")
    flag = value.get("ring_to_open_enabled")
    duration = value.get("duration_seconds")
    result = RingUnlockSettings(
        mode=mode if isinstance(mode, str) and MODE.fullmatch(mode) else None,
        ring_to_open_enabled=flag if isinstance(flag, bool) else None,
        duration_seconds=(
            duration
            if isinstance(duration, int)
            and not isinstance(duration, bool)
            and 0 <= duration <= MAX_DURATION_SECONDS
            else None
        ),
    )
    if result == RingUnlockSettings(None, None, None):
        return None
    return result
