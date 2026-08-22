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


@dataclass(frozen=True, slots=True)
class Recording:
    """One private Ring call recording."""

    recording_id: str
    event_at: int
    saved_at: int
    bytes: int
    media_type: str


@dataclass(frozen=True, slots=True)
class RecordingImport:
    """One bounded asynchronous Ring recording import."""

    import_id: str
    state: str
    recording_id: str | None


def parse_audio_session(payload: dict) -> AudioSession:
    """Validate the bounded WebRTC answer."""
    from .client import JSON_LIMIT
    from .errors import CannotConnectError

    try:
        candidates = tuple(
            IceCandidate(str(item["candidate"]), int(item["sdp_mline_index"]))
            for item in payload["ice_candidates"]
        )
        result = AudioSession(
            str(payload["session_id"]),
            str(payload["answer_sdp"]),
            candidates,
            int(payload["expires_in"]),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise CannotConnectError from error
    invalid_candidate = any(
        not item.candidate or len(item.candidate) > 4096 or not 0 <= item.sdp_mline_index <= 16
        for item in result.ice_candidates
    )
    if (
        not result.session_id
        or not result.answer_sdp.startswith("v=0")
        or len(result.answer_sdp) > JSON_LIMIT
        or len(result.ice_candidates) > 64
        or not 1 <= result.expires_in <= 120
        or invalid_candidate
    ):
        raise CannotConnectError
    return result


def parse_recordings(payload: dict) -> tuple[Recording, ...]:
    """Validate a bounded recording inventory without media URLs."""
    from .errors import CannotConnectError

    try:
        raw = payload["recordings"]
        if not isinstance(raw, list) or len(raw) > 4096:
            raise CannotConnectError
        result = tuple(
            Recording(
                str(item["recording_id"]),
                int(item["event_at"]),
                int(item["saved_at"]),
                int(item["bytes"]),
                str(item["media_type"]),
            )
            for item in raw
        )
    except (KeyError, TypeError, ValueError) as error:
        raise CannotConnectError from error
    if any(
        not item.recording_id
        or item.bytes < 1024
        or item.bytes > 64 * 1024 * 1024
        or item.media_type != "audio/mp4"
        for item in result
    ):
        raise CannotConnectError
    return result


def parse_recording_import(payload: dict) -> RecordingImport:
    """Validate one recording-import transition."""
    from .errors import CannotConnectError

    try:
        result = RecordingImport(
            import_id=str(payload["import_id"]),
            state=str(payload["state"]),
            recording_id=(str(payload["recording_id"]) if payload["recording_id"] else None),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise CannotConnectError from error
    if not result.import_id or result.state not in {
        "pending",
        "complete",
        "unavailable",
        "expired",
        "failed",
    }:
        raise CannotConnectError
    return result
