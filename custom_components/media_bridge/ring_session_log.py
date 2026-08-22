"""Bounded Home Assistant event and Logbook audit for Ring communications."""

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from time import monotonic

from homeassistant.components import logbook
from homeassistant.core import HomeAssistant

from .const import DOMAIN

EVENT_STARTED = "vistoda_ring_communication_started"
EVENT_ENDED = "vistoda_ring_communication_ended"
SESSION_LOG_KEY = "ring_session_log"
MAX_ACTIVE_RECORDS = 32


@dataclass(frozen=True, slots=True)
class SessionRecord:
    """Private in-memory timing record for one browser session."""

    alias: str
    reference: str
    mode: str
    ice_gathering_ms: int
    started_at: str
    monotonic_started: float


def session_reference(session_id: str) -> str:
    """Return a non-reversible correlation value, never the bridge UUID."""
    return sha256(session_id.encode()).hexdigest()[:12]


def async_started(
    hass: HomeAssistant,
    alias: str,
    session_id: str,
    mode: str,
    ice_gathering_ms: int,
) -> None:
    """Record and publish one successfully negotiated communication."""
    records = hass.data[DOMAIN].setdefault(SESSION_LOG_KEY, {})
    while len(records) >= MAX_ACTIVE_RECORDS:
        records.pop(next(iter(records)))
    now = datetime.now(UTC).isoformat()
    record = SessionRecord(
        alias=alias,
        reference=session_reference(session_id),
        mode=mode,
        ice_gathering_ms=ice_gathering_ms,
        started_at=now,
        monotonic_started=monotonic(),
    )
    records[session_id] = record
    payload = {
        "alias": alias,
        "session_reference": record.reference,
        "mode": mode,
        "ice_gathering_ms": ice_gathering_ms,
        "started_at": now,
    }
    hass.bus.async_fire(EVENT_STARTED, payload)
    logbook.async_log_entry(
        hass,
        "Vistoda · Ring",
        f"Comunicazione avviata · {mode} · ICE {ice_gathering_ms} ms",
        DOMAIN,
    )


def async_ended(
    hass: HomeAssistant,
    session_id: str,
    reason: str,
    bridge_acknowledged: bool,
) -> None:
    """Publish one termination only when its matching start was recorded."""
    records = hass.data[DOMAIN].setdefault(SESSION_LOG_KEY, {})
    record = records.pop(session_id, None)
    if not isinstance(record, SessionRecord):
        return
    duration_ms = max(0, round((monotonic() - record.monotonic_started) * 1_000))
    payload = {
        "alias": record.alias,
        "session_reference": record.reference,
        "mode": record.mode,
        "ice_gathering_ms": record.ice_gathering_ms,
        "duration_ms": duration_ms,
        "reason": reason,
        "bridge_acknowledged": bridge_acknowledged,
        "ended_at": datetime.now(UTC).isoformat(),
    }
    hass.bus.async_fire(EVENT_ENDED, payload)
    suffix = "ACK bridge" if bridge_acknowledged else "chiusura locale"
    logbook.async_log_entry(
        hass,
        "Vistoda · Ring",
        f"Comunicazione terminata · {duration_ms / 1_000:.1f} s · {reason} · {suffix}",
        DOMAIN,
    )
