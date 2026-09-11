"""On-demand EZVIZ camera entity backed by the Rust bridge."""

from homeassistant.components.camera import Camera, CameraEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import BridgeRuntime
from .const import CONF_ALIAS, CONF_PROVIDER, DOMAIN, PROVIDER_EZVIZ
from .ezviz_identity import device_info, entity_prefix


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add a camera only for bridges with a verified video contract."""
    if entry.data[CONF_PROVIDER] != PROVIDER_EZVIZ:
        return
    runtime: BridgeRuntime = hass.data[DOMAIN][entry.entry_id]
    if runtime.client is None:
        return
    async_add_entities([EzvizBridgeCamera(runtime, entry)])


class EzvizBridgeCamera(CoordinatorEntity, Camera):
    """Manually refreshed snapshot plus shared copy-remuxed MPEG-TS live view."""

    _attr_has_entity_name = True
    _attr_name = "Live"
    _attr_supported_features = CameraEntityFeature.STREAM

    def __init__(self, runtime: BridgeRuntime, entry: ConfigEntry) -> None:
        CoordinatorEntity.__init__(self, runtime.coordinator)
        Camera.__init__(self)
        assert runtime.client is not None
        self._client = runtime.client
        self._runtime = runtime
        self._entry = entry
        self._alias = entry.data[CONF_ALIAS]
        self._entry_id = entry.entry_id
        self._attr_unique_id = f"{entity_prefix(entry)}bridge-camera"
        self._attr_device_info = device_info(entry)

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return only the last snapshot explicitly requested by the user."""
        return self._runtime.snapshots.get(self._alias)

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Expose the manual snapshot timestamp without leaking storage details."""
        updated_at = self._runtime.snapshot_updated_at.get(self._alias)
        attributes = {"alias": self._alias, "entry_id": self._entry_id}
        if updated_at:
            attributes["snapshot_updated_at"] = updated_at
        return attributes

    async def stream_source(self) -> str:
        """Give HA Stream the authenticated private MPEG-TS source."""
        from .ezviz_binding import CONF_EZVIZ_SOURCE_ID, async_verify_native, source_binding

        await async_verify_native(self._entry, self._client)
        expected = source_binding(self._entry.data[CONF_EZVIZ_SOURCE_ID])
        return self._client.stream_url(self._alias, expected)
