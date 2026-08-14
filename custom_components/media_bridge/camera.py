"""On-demand EZVIZ camera entity backed by the Rust bridge."""

from homeassistant.components.camera import Camera, CameraEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import BridgeRuntime
from .const import CONF_ALIAS, CONF_PROVIDER, DOMAIN, PROVIDER_EZVIZ
from .errors import BridgeError


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
    async_add_entities([EzvizBridgeCamera(runtime, entry.data[CONF_ALIAS])])


class EzvizBridgeCamera(CoordinatorEntity, Camera):
    """Fresh snapshot plus shared copy-remuxed MPEG-TS live view."""

    _attr_has_entity_name = True
    _attr_name = "Live"
    _attr_supported_features = CameraEntityFeature.STREAM

    def __init__(self, runtime: BridgeRuntime, alias: str) -> None:
        CoordinatorEntity.__init__(self, runtime.coordinator)
        Camera.__init__(self)
        assert runtime.client is not None
        self._client = runtime.client
        self._alias = alias
        self._attr_unique_id = f"ezviz-{alias}-bridge-camera"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"ezviz:{alias}")},
            "name": "Vistoda · EZVIZ",
            "manufacturer": "EZVIZ",
            "model": "Vistoda VTM bridge",
        }

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Fetch a bounded fresh snapshot."""
        try:
            return await self._client.snapshot(self._alias)
        except BridgeError:
            return None

    async def stream_source(self) -> str:
        """Give HA Stream the authenticated private MPEG-TS source."""
        return self._client.stream_url(self._alias)
