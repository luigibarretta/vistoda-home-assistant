"""Exactly-once missed Ring call publication for user automations."""

import time

EVENT_RING_MISSED_CALL = "vistoda_ring_missed_call"
STORE_FIELD = "last_missed_ding_at"
# Without a persisted baseline, an old engine value is history, not a new call.
FIRST_SEEN_MAX_AGE = 15 * 60


async def async_publish_missed_call(history, occurred_at: int, now: float | None = None) -> bool:
    """Fire one bus event per new missed ding, persisted in the entry history store."""
    await history._async_load()
    async with history._lock:
        last = history._data.get(STORE_FIELD)
        baseline = isinstance(last, int) and not isinstance(last, bool)
        if baseline and occurred_at <= last:
            return False
        history._data[STORE_FIELD] = occurred_at
        await history._store.async_save(history._data)
    current = time.time() if now is None else now
    if not baseline and current - occurred_at > FIRST_SEEN_MAX_AGE:
        return False
    history.hass.bus.async_fire(
        EVENT_RING_MISSED_CALL,
        {
            **history.identity,
            "entry_id": history.entry.entry_id,
            "alias": history.alias,
            "occurred_at": occurred_at,
        },
    )
    return True
