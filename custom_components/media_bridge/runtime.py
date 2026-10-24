"""Typed per-entry runtime stored on ``ConfigEntry.runtime_data``.

Everything one config entry owns lives here and disappears with the entry:
Home Assistant deletes ``runtime_data`` after a successful unload. Only
genuinely domain-wide state stays in ``hass.data[DOMAIN]``: the YAML discovery
tokens, the shared USB backup locks, the recording-list stores (one Store each,
keyed by entry inside), and the bounded Ring session log keyed by browser session.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

    from .client import BridgeClient
    from .coordinator import BridgeCoordinator
    from .ezviz_account import EzvizDefenceCoordinator
    from .ezviz_alarm_listener import EzvizAlarmListener
    from .ezviz_controls import EzvizControlsCoordinator
    from .ezviz_media import EzvizMediaCoordinator
    from .local import BlinkAdapterCoordinator
    from .ring_event_listener import RingEventListener
    from .ring_history import RingHistoryManager
    from .ring_status import RingStatusCoordinator


@dataclass(slots=True)
class BridgeRuntime:
    """Runtime owned by one config entry."""

    client: BridgeClient | None
    coordinator: BridgeCoordinator | BlinkAdapterCoordinator
    ring_status: RingStatusCoordinator | None = None
    ring_events: RingEventListener | None = None
    ring_history: RingHistoryManager | None = None
    ezviz_alarms: EzvizAlarmListener | None = None
    ezviz_media: EzvizMediaCoordinator | None = None
    ezviz_controls: EzvizControlsCoordinator | None = None
    ezviz_defence: EzvizDefenceCoordinator | None = None
    panel_url: str | None = None
    snapshots: dict[str, bytes] = field(default_factory=dict)
    snapshot_updated_at: dict[str, str] = field(default_factory=dict)
    # Last hourly Blink network-backup pass, in memory like before.
    usb_backup_status: dict[str, Any] | None = None


type MediaBridgeConfigEntry = ConfigEntry[BridgeRuntime]


def entry_runtime(entry: Any) -> BridgeRuntime | None:
    """Return the runtime of one of our entries, or None when it is not set up."""
    if entry is None or getattr(entry, "domain", DOMAIN) != DOMAIN:
        return None
    return getattr(entry, "runtime_data", None)


def runtime_for(hass: HomeAssistant, entry_id: Any) -> BridgeRuntime | None:
    """Look an entry up by id; unknown, foreign or not-loaded entries give None."""
    entries = getattr(hass, "config_entries", None)
    if entries is None or not isinstance(entry_id, str):
        return None
    return entry_runtime(entries.async_get_entry(entry_id))
