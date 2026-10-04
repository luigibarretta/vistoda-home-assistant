"""Bridge, Ring Intercom and EZVIZ camera connectivity entities."""

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import BridgeRuntime
from .const import CONF_ALIAS, CONF_PROVIDER, DOMAIN, PROVIDER_BLINK, PROVIDER_EZVIZ, PROVIDER_RING


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add bridge connectivity plus the physical device connectivity when known."""
    runtime: BridgeRuntime = hass.data[DOMAIN][entry.entry_id]
    entities: list[BinarySensorEntity] = [BridgeConnectivity(runtime, entry)]
    provider = entry.data[CONF_PROVIDER]
    if provider == PROVIDER_RING and runtime.ring_status is not None:
        entities.append(RingIntercomConnectivity(runtime, entry))
    if provider == PROVIDER_EZVIZ:
        entities.append(EzvizCameraConnectivity(entry))
    async_add_entities(entities)
    media = getattr(runtime, "ezviz_media", None)
    if provider == PROVIDER_EZVIZ and media is not None:
        from .entity_gate import async_add_when_supported
        from .ezviz_media import reports_storage
        from .ezviz_media_entities import EzvizMicroSdProblem

        # The sensor platform starts the first poll; this only waits for support.
        async_add_when_supported(
            entry,
            media,
            reports_storage,
            lambda: [EzvizMicroSdProblem(media, entry)],
            async_add_entities,
        )


class BridgeConnectivity(CoordinatorEntity, BinarySensorEntity):
    """Report whether the private bridge answers its health contract."""

    _attr_has_entity_name = True
    _attr_name = "Audio Vistoda"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, runtime: BridgeRuntime, entry: ConfigEntry) -> None:
        super().__init__(runtime.coordinator)
        provider = entry.data[CONF_PROVIDER]
        alias = entry.data[CONF_ALIAS]
        self._provider = provider
        self._attr_unique_id = f"{provider}-{alias}-bridge-connectivity"
        local = provider == PROVIDER_BLINK
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{provider}:{alias}")},
            "name": f"Vistoda · {provider.upper()}",
            "manufacturer": "Vistoda",
            "model": "Local Home Assistant adapter" if local else "Private Rust bridge",
        }
        if provider == "ring":
            from .ring_binding import entity_prefix
            from .ring_facade import ring_device_info

            self._attr_unique_id = f"{entity_prefix(entry)}bridge-connectivity"
            self._attr_device_info = ring_device_info(entry)
        if provider == "ezviz":
            from .ezviz_identity import device_info, entity_prefix

            self._attr_unique_id = f"{entity_prefix(entry)}bridge-connectivity"
            self._attr_device_info = device_info(entry)
        if runtime.panel_url:
            self._attr_device_info["configuration_url"] = runtime.panel_url

    @property
    def is_on(self) -> bool:
        """Return current coordinator success."""
        return self.coordinator.last_update_success

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Expose only non-secret version metadata."""
        key = "cameras" if self._attr_unique_id.startswith("blink-") else "version"
        attributes = {key: self.coordinator.data or "unknown"}
        attributes["panel_path"] = f"/vistoda/{self._provider}"
        attributes["connectivity_scope"] = "bridge"
        if self._provider == "ring":
            attributes.update(
                {
                    "audio_modes": "listen,talk",
                    "full_duplex": "true",
                }
            )
        return attributes


class RingIntercomConnectivity(CoordinatorEntity, BinarySensorEntity):
    """Report the Ring Intercom's own cloud connectivity from native status."""

    _attr_has_entity_name = True
    _attr_translation_key = "ring_intercom_connectivity"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, runtime: BridgeRuntime, entry: ConfigEntry) -> None:
        from .ring_binding import entity_prefix
        from .ring_facade import ring_device_info

        super().__init__(runtime.ring_status)
        self._entry = entry
        self._attr_unique_id = f"{entity_prefix(entry)}intercom-connectivity"
        self._attr_device_info = ring_device_info(entry)
        self._attr_extra_state_attributes = {"connectivity_scope": "device"}

    @property
    def available(self) -> bool:
        """Stay unavailable when the bridge or the enrolled device cannot be verified."""
        from .ring_binding import verified_device_id

        return (
            self.coordinator.last_update_success
            and verified_device_id(self._entry, self.coordinator.data) is not None
        )

    @property
    def is_on(self) -> bool | None:
        """Return the native online flag."""
        return getattr(self.coordinator.data, "online", None)


class EzvizCameraConnectivity(BinarySensorEntity):
    """Report camera reachability from Home Assistant's native EZVIZ coordinator."""

    _attr_has_entity_name = True
    _attr_translation_key = "ezviz_camera_connectivity"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_should_poll = True
    _attr_available = False

    def __init__(self, entry: ConfigEntry) -> None:
        from .ezviz_identity import device_info, entity_prefix

        self._entry = entry
        self._attr_unique_id = f"{entity_prefix(entry)}camera-connectivity"
        self._attr_device_info = device_info(entry)
        self._attr_extra_state_attributes = {
            "connectivity_scope": "camera",
            "source_integration": "ezviz",
        }

    async def async_added_to_hass(self) -> None:
        """Publish a real first state instead of waiting for the first poll."""
        await super().async_added_to_hass()
        await self.async_update()

    async def async_update(self) -> None:
        """Read the in-memory native snapshot; this never calls the EZVIZ cloud."""
        from .ezviz_core import native_camera_online

        online = native_camera_online(self.hass, self._entry)
        self._attr_available = online is not None
        self._attr_is_on = online
