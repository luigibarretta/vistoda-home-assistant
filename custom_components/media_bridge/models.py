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
    started_at: int
    ended_at: int
    saved_at: int
    bytes: int
    media_type: str
    storage_path: str | None = None


@dataclass(frozen=True, slots=True)
class RecordingStorage:
    """User-facing location of the bounded Ring archive."""

    kind: str
    directory: str
    user_visible: bool


@dataclass(frozen=True, slots=True)
class RecordingArchive:
    """Validated recording inventory and its effective storage."""

    recordings: tuple[Recording, ...]
    storage: RecordingStorage | None


@dataclass(frozen=True, slots=True)
class RingStatus:
    """Bounded Ring Intercom status from the native Rust provider."""

    battery: int | None
    online: bool
    doorbell_volume: int | None
    mic_volume: int | None
    voice_volume: int | None
    last_activity: int | None


def parse_ring_status(payload: dict) -> RingStatus:
    """Validate native battery, connectivity, volumes and activity."""
    from .errors import CannotConnectError

    try:
        result = RingStatus(
            battery=_optional_int(payload["battery"]),
            online=payload["online"],
            doorbell_volume=_optional_int(payload["doorbell_volume"]),
            mic_volume=_optional_int(payload["mic_volume"]),
            voice_volume=_optional_int(payload["voice_volume"]),
            last_activity=_optional_int(payload["last_activity"]),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise CannotConnectError from error
    if not isinstance(result.online, bool) or not _valid_ring_status(result):
        raise CannotConnectError
    return result


def _optional_int(value) -> int | None:
    return None if value is None else int(value)


def _valid_ring_status(status: RingStatus) -> bool:
    values = (
        (status.battery, 100),
        (status.doorbell_volume, 8),
        (status.mic_volume, 11),
        (status.voice_volume, 11),
    )
    return all(value is None or 0 <= value <= maximum for value, maximum in values) and (
        status.last_activity is None or status.last_activity >= 0
    )


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


def parse_recording_archive(payload: dict) -> RecordingArchive:
    """Validate bounded archive metadata and optional storage paths."""
    from .errors import CannotConnectError

    try:
        raw = payload["recordings"]
        if not isinstance(raw, list) or len(raw) > 4096:
            raise CannotConnectError
        result = tuple(parse_recording(item) for item in raw)
    except (KeyError, TypeError, ValueError) as error:
        raise CannotConnectError from error
    if any(
        not item.recording_id
        or item.bytes < 128
        or item.bytes > 8 * 1024 * 1024
        or item.media_type not in {"audio/mp4", "audio/webm"}
        for item in result
    ):
        raise CannotConnectError
    storage = _parse_recording_storage(payload.get("storage"))
    if storage is not None and any(
        item.storage_path is None or not item.storage_path.startswith(f"{storage.directory}/")
        for item in result
    ):
        raise CannotConnectError
    return RecordingArchive(result, storage)


def _parse_recording_storage(value) -> RecordingStorage | None:
    from .errors import CannotConnectError

    if value is None:
        return None
    try:
        result = RecordingStorage(
            str(value["kind"]), str(value["directory"]), value["user_visible"]
        )
    except (KeyError, TypeError, ValueError) as error:
        raise CannotConnectError from error
    if (
        result.kind not in {"private", "addon_config", "media", "share", "custom"}
        or not isinstance(result.user_visible, bool)
        or not result.directory.startswith("/")
        or result.directory.endswith("/")
        or len(result.directory) > 1024
        or any(not character.isprintable() for character in result.directory)
        or "/../" in f"{result.directory}/"
        or "/./" in f"{result.directory}/"
    ):
        raise CannotConnectError
    return result


def parse_recording(item: dict) -> Recording:
    """Validate one locally archived recording."""
    from .errors import CannotConnectError

    try:
        result = Recording(
            str(item["recording_id"]),
            int(item["started_at"]),
            int(item["ended_at"]),
            int(item["saved_at"]),
            int(item["bytes"]),
            str(item["media_type"]),
            None if item.get("storage_path") is None else str(item["storage_path"]),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise CannotConnectError from error
    if (
        not result.recording_id
        or result.started_at > result.ended_at
        or not 128 <= result.bytes <= 8 * 1024 * 1024
        or result.media_type not in {"audio/mp4", "audio/webm"}
        or (
            result.storage_path is not None
            and (
                not result.storage_path.startswith("/")
                or len(result.storage_path) > 1100
                or any(not character.isprintable() for character in result.storage_path)
                or "/../" in f"{result.storage_path}/"
                or "/./" in f"{result.storage_path}/"
            )
        )
    ):
        raise CannotConnectError
    return result
