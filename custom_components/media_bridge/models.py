"""Small immutable bridge models."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Enrollment:
    """Enrollment transition returned by the bridge."""

    enrollment_id: str
    next_step: str
    expires_in: int


@dataclass(frozen=True, slots=True)
class BridgeHealth:
    """Redacted bridge health."""

    version: str
