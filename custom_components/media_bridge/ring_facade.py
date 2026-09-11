"""Shared official Ring entity facade without a second cloud session."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Event, HomeAssistant, State, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_state_change_event

from .const import CONF_ALIAS, CONF_RING_DELEGATE_CONTROLS, DOMAIN, SIGNAL_RING_POLICY_CHANGED
from .ring_binding import (
    CONF_RING_DEVICE_ID,
    CONF_RING_OFFICIAL_BINDING,
    device_identifier,
    entity_prefix,
    verified_device_id,
)
from .ring_contract import (
    DOORBELL_VOLUME,
    MIC_VOLUME,
    OPEN_DOOR,
    VOICE_VOLUME,
    RingSourceCandidate,
    RingSourceSpec,
    select_ring_source,
)

_LOGGER = logging.getLogger(__name__)
ATTRIBUTION = "Delegated to the official Home Assistant Ring integration"


def ring_device_info(entry) -> dict[str, Any]:
    """Return the single enhanced Vistoda Ring device identity."""
    return {
        "identifiers": {device_identifier(entry)},
        "name": "Vistoda · RING",
        "manufacturer": "Vistoda",
        "model": "Ring Intercom enhanced bridge",
    }


def resolve_source(hass: HomeAssistant, spec: RingSourceSpec, entry) -> str | None:
    """Resolve an official Ring Intercom entity from supported registries."""
    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)
    binding = entry.data.get(CONF_RING_OFFICIAL_BINDING)
    device_id = entry.data.get(CONF_RING_DEVICE_ID)
    if not binding or not device_id:
        return None
    candidates = []
    for entity in entity_registry.entities.values():
        if (
            entity.device_id != binding.get("device_id")
            or entity.config_entry_id != binding.get("config_entry_id")
            or entity.disabled_by is not None
            or not entity.unique_id.startswith(f"{device_id}-")
        ):
            continue
        device = device_registry.async_get(entity.device_id) if entity.device_id else None
        candidates.append(
            RingSourceCandidate(
                entity_id=entity.entity_id,
                platform=entity.platform,
                manufacturer=device.manufacturer if device else None,
                model=device.model if device else None,
                translation_key=entity.translation_key,
                original_name=entity.original_name,
            )
        )
    source = select_ring_source(candidates, spec)
    if source is None:
        _LOGGER.warning("Official Ring Intercom source is missing or ambiguous: %s", spec.key)
    return source


def official_controls_available(hass: HomeAssistant, entry) -> bool:
    """Require every official entity used by the delegated control path."""
    return all(
        resolve_source(hass, spec, entry) is not None
        for spec in (OPEN_DOOR, DOORBELL_VOLUME, MIC_VOLUME, VOICE_VOLUME)
    )


def async_bind_official(hass: HomeAssistant, entry) -> None:
    """Bind only the official entity for the exact native Ring device ID."""
    device_id = entry.data.get(CONF_RING_DEVICE_ID)
    if not device_id or entry.data.get(CONF_RING_OFFICIAL_BINDING):
        return
    registry = er.async_get(hass)
    devices = dr.async_get(hass)
    matches = []
    for entity in registry.entities.values():
        device = devices.async_get(entity.device_id) if entity.device_id else None
        if (
            entity.platform == "ring"
            and entity.unique_id == f"{device_id}-open_door"
            and entity.entity_id.startswith("button.")
            and entity.disabled_by is None
            and device
            and device.manufacturer == "Ring"
            and device.model == "Intercom"
        ):
            matches.append(entity)
    if len(matches) == 1:
        source = matches[0]
        hass.config_entries.async_update_entry(
            entry,
            data={
                **entry.data,
                CONF_RING_OFFICIAL_BINDING: {
                    "device_id": source.device_id,
                    "config_entry_id": source.config_entry_id,
                    "unique_id": source.unique_id,
                },
            },
        )


class RingFacadeEntity(Entity):
    """Mirror one official entity on the enhanced Vistoda device."""

    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION
    _attr_should_poll = False
    _attr_native_capable = False

    def __init__(self, hass: HomeAssistant, entry, spec: RingSourceSpec) -> None:
        self._hass = hass
        self._entry = entry
        self._alias = entry.data[CONF_ALIAS]
        self._spec = spec
        self._source_entity_id = resolve_source(hass, spec, entry)
        self._attr_unique_id = f"{entity_prefix(entry)}facade-{spec.key}"
        self._attr_device_info = ring_device_info(entry)

    @property
    def delegated(self) -> bool:
        """Return the global control-source policy."""
        return bool(self._entry.options.get(CONF_RING_DELEGATE_CONTROLS, False))

    @property
    def native_status(self):
        """Return the shared native status snapshot, when healthy."""
        runtime = self._hass.data[DOMAIN][self._entry.entry_id]
        coordinator = runtime.ring_status
        if (
            coordinator is None
            or not coordinator.last_update_success
            or verified_device_id(self._entry, coordinator.data) is None
        ):
            return None
        return coordinator.data

    @property
    def source_state(self) -> State | None:
        """Return the current provider-owned source state."""
        if (
            self._source_entity_id is None
            or resolve_source(self._hass, self._spec, self._entry) != self._source_entity_id
        ):
            return None
        return self.hass.states.get(self._source_entity_id)

    @property
    def available(self) -> bool:
        """Stay unavailable when the provider source is not usable."""
        if self._attr_native_capable and not self.delegated:
            return self.native_status is not None
        state = self.source_state
        return state is not None and state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Make delegation explicit without exposing credentials."""
        if self._attr_native_capable and not self.delegated:
            return {"control_source": "vistoda_native", "source_integration": DOMAIN}
        return {
            "control_source": "official_ring",
            "source_entity_id": self._source_entity_id,
            "source_integration": "ring",
        }

    async def refresh_native_status(self) -> None:
        """Refresh the shared native snapshot after one bounded mutation."""
        coordinator = self._hass.data[DOMAIN][self._entry.entry_id].ring_status
        if coordinator is not None:
            await coordinator.async_request_refresh()

    async def async_added_to_hass(self) -> None:
        """Follow the source without polling Ring a second time."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_RING_POLICY_CHANGED, self._policy_changed)
        )
        coordinator = self._hass.data[DOMAIN][self._entry.entry_id].ring_status
        if self._attr_native_capable and coordinator is not None:
            self.async_on_remove(coordinator.async_add_listener(self.async_write_ha_state))
        if self._source_entity_id:
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass, [self._source_entity_id], self._source_changed
                )
            )

    @callback
    def _policy_changed(self, entry_id: str) -> None:
        """Publish the newly selected provider path immediately."""
        if entry_id == self._entry.entry_id:
            self.async_write_ha_state()

    @callback
    def _source_changed(self, event: Event) -> None:
        """Refresh or forward one provider state transition."""
        self.handle_source_event(event)

    @callback
    def handle_source_event(self, event: Event) -> None:
        """Default state mirror callback."""
        self.async_write_ha_state()

    async def call_source_service(self, domain: str, service: str, data: dict) -> None:
        """Delegate one bounded action to the official integration entity."""
        if not self.available or self._source_entity_id is None:
            raise RuntimeError("Official Ring Intercom entity is unavailable")
        await self.hass.services.async_call(
            domain,
            service,
            {**data, "entity_id": self._source_entity_id},
            blocking=True,
            context=self._context,
        )
