"""Continuous-outage grace for repairs that would otherwise page a person on a blip."""

import time

# Provider, network and add-on restarts heal on their own within minutes. Only an
# outage that stays continuous this long is worth a repair (and a phone alert).
OUTAGE_GRACE_SECONDS = 900

# Process-wide on purpose: an entry that keeps failing setup is recreated on
# every retry, but its outage must keep the same start time.
_CLOCKS: dict[str, "OutageClock"] = {}


class OutageClock:
    """Track one continuous outage with a monotonic start time."""

    def __init__(self, grace: float = OUTAGE_GRACE_SECONDS) -> None:
        self.grace = grace
        self.since: float | None = None

    def down(self) -> bool:
        """Record a failed observation; return whether the outage passed the grace."""
        now = time.monotonic()
        if self.since is None:
            self.since = now
        return now - self.since >= self.grace

    def up(self) -> None:
        """A single success ends the outage."""
        self.since = None


def outage_clock(key: str) -> OutageClock:
    """Return the shared clock for one issue id."""
    return _CLOCKS.setdefault(key, OutageClock())


def forget_outages(suffix: str) -> None:
    """Drop the clocks of a removed config entry."""
    for key in [key for key in _CLOCKS if key.endswith(suffix)]:
        del _CLOCKS[key]
