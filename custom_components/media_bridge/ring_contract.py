"""Pure contract for the official Ring Intercom facade."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RingSourceSpec:
    """One official Ring entity required by the Vistoda facade."""

    key: str
    domain: str
    translation_key: str | None
    original_name: str


@dataclass(frozen=True, slots=True)
class RingSourceCandidate:
    """Registry fields needed for deterministic source selection."""

    entity_id: str
    platform: str
    manufacturer: str | None
    model: str | None
    translation_key: str | None
    original_name: str | None


OPEN_DOOR = RingSourceSpec("open_door", "button", "open_door", "Open door")
DING = RingSourceSpec("ding", "event", "ding", "Ding")
INTERCOM_UNLOCK = RingSourceSpec("intercom_unlock", "event", "intercom_unlock", "Intercom unlock")
DOORBELL_VOLUME = RingSourceSpec("doorbell_volume", "number", "doorbell_volume", "Doorbell volume")
MIC_VOLUME = RingSourceSpec("mic_volume", "number", "mic_volume", "Mic volume")
VOICE_VOLUME = RingSourceSpec("voice_volume", "number", "voice_volume", "Voice volume")
BATTERY = RingSourceSpec("battery", "sensor", None, "Battery")
LAST_ACTIVITY = RingSourceSpec("last_activity", "sensor", "last_activity", "Last activity")

ACTIVE_RING_SOURCES = (
    OPEN_DOOR,
    DING,
    INTERCOM_UNLOCK,
    DOORBELL_VOLUME,
    MIC_VOLUME,
    VOICE_VOLUME,
    BATTERY,
    LAST_ACTIVITY,
)


def select_ring_source(candidates: list[RingSourceCandidate], spec: RingSourceSpec) -> str | None:
    """Return one exact official Ring Intercom entity, failing closed on ambiguity."""
    matches = [
        candidate.entity_id
        for candidate in candidates
        if candidate.platform == "ring"
        and candidate.entity_id.startswith(f"{spec.domain}.")
        and candidate.manufacturer == "Ring"
        and candidate.model == "Intercom"
        and (
            candidate.translation_key == spec.translation_key
            if spec.translation_key is not None
            else candidate.original_name == spec.original_name
        )
    ]
    return matches[0] if len(matches) == 1 else None
