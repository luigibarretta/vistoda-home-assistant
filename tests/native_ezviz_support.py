"""Home Assistant's official EZVIZ integration as Vistoda may see it: registries and states.

The fake native entry raises on runtime_data, so any test that reaches into the
official integration's runtime objects fails.
"""

import sys
from types import SimpleNamespace

SERIAL = "BC1234567"
CAMERA = "camera.front_door"
LOADED = SimpleNamespace(value="loaded")


class NativeEntry:
    domain = "ezviz"

    def __init__(self, entry_id="native", state=LOADED):
        self.entry_id, self.state = entry_id, state

    @property
    def runtime_data(self):
        raise AssertionError("runtime_data belongs to the official EZVIZ integration")


class NativeEzviz:
    """Device and entity registries, camera state and the camera services."""

    def __init__(self, *, entries=None, serial=SERIAL, online=True, defence=False, camera=True):
        self.entries = [NativeEntry()] if entries is None else entries
        self.serial, self.online, self.defence = serial, online, defence
        self.camera, self.calls, self.sticky, self.fail = camera, [], False, None
        self.disabled_by = None

    def device(self, identifier, entry_id):
        owners = {entry.entry_id for entry in self.entries}
        if identifier != ("ezviz", self.serial) or entry_id not in owners:
            return None
        return SimpleNamespace(
            id=f"device-{entry_id}",
            name="Front door",
            name_by_user=None,
            area_id=None,
        )

    def registry_entities(self) -> dict:
        if not self.camera or not self.entries:
            return {}
        entity = SimpleNamespace(
            config_entry_id=self.entries[0].entry_id,
            device_id=f"device-{self.entries[0].entry_id}",
            disabled_by=self.disabled_by,
            entity_id=CAMERA,
            unique_id=self.serial,
            name=None,
            original_name=None,
            original_device_class=None,
        )
        return {CAMERA: entity}

    def state(self, entity_id):
        if entity_id != CAMERA or not self.camera:
            return None
        attributes = {"motion_detection": True} if self.defence else {}
        return SimpleNamespace(
            entity_id=CAMERA,
            state="idle" if self.online else "unavailable",
            attributes=attributes,
        )

    async def async_call(self, domain, service, data, blocking=False, context=None):
        self.calls.append((domain, service, data["entity_id"]))
        if self.fail is not None:
            raise self.fail
        if domain == "camera" and not self.sticky:
            self.defence = service == "enable_motion_detection"

    def install(self, hass) -> None:
        """Wire the registries, states and services into hass and the stub modules."""
        registry = sys.modules["homeassistant.helpers.device_registry"].async_get(hass)
        registry.async_get_device_by_identifier = self.device
        registry.entities = self.registry_entities()
        hass.states = SimpleNamespace(get=self.state)
        hass.services = SimpleNamespace(async_call=self.async_call)
        by_id = {entry.entry_id: entry for entry in self.entries}
        previous = getattr(hass.config_entries, "async_get_entry", None)

        def async_get_entry(entry_id):
            if entry_id in by_id:
                return by_id[entry_id]
            return previous(entry_id) if previous else None

        hass.config_entries.async_get_entry = async_get_entry
        others = getattr(hass.config_entries, "async_entries", None)

        def async_entries(domain=None):
            if domain == "ezviz":
                return list(self.entries)
            return others(domain) if others else []

        hass.config_entries.async_entries = async_entries
