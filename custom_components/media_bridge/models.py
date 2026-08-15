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


@dataclass(frozen=True, slots=True)
class IceCandidate:
    """One bounded remote ICE candidate."""

    candidate: str
    sdp_mline_index: int


@dataclass(frozen=True, slots=True)
class AudioSession:
    """Negotiated Ring audio session returned to an HA user."""

    session_id: str
    answer_sdp: str
    ice_candidates: tuple[IceCandidate, ...]
    expires_in: int
