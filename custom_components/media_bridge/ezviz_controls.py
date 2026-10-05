"""Per-camera EZVIZ controls polled from the Vistoda EZVIZ app (0.10+)."""

import logging
from dataclasses import dataclass
from datetime import timedelta

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client_ezviz_controls import EzvizControls
from .client_ezviz_media import EzvizFeatureUnsupportedError
from .const import CONF_ALIAS, DOMAIN
from .errors import BridgeError, ReauthRequiredError

_LOGGER = logging.getLogger(__name__)
CONTROLS_INTERVAL = timedelta(seconds=60)
BATTERY_SUFFIX = "battery"


@dataclass(frozen=True, slots=True)
class EzvizControlsStatus:
    """supported=False: the app predates /controls; standalone controls are unavailable."""

    supported: bool
    controls: EzvizControls | None = None


UNSUPPORTED = EzvizControlsStatus(False)


def supports_controls(data) -> bool:
    return isinstance(data, EzvizControlsStatus) and data.supported


def controls_of(data) -> EzvizControls | None:
    return data.controls if supports_controls(data) else None


def reports_battery(data) -> bool:
    controls = controls_of(data)
    return controls is not None and controls.battery_percent is not None


def runtime_controls(hass, entry_id: str):
    """Return the entry's controls coordinator, if the entry is a loaded EZVIZ camera."""
    runtime = getattr(hass, "data", {}).get(DOMAIN, {}).get(entry_id)
    return getattr(runtime, "ezviz_controls", None)


def app_controls(hass, entry_id: str):
    """Return the coordinator only while the app answers /controls successfully."""
    coordinator = runtime_controls(hass, entry_id)
    if coordinator is None or not supports_controls(coordinator.data):
        return None
    return coordinator if coordinator.last_update_success else None


def app_camera_online(hass, entry_id: str) -> bool | None:
    coordinator = app_controls(hass, entry_id)
    controls = controls_of(coordinator.data) if coordinator else None
    return controls.online if controls else None


def controls_payload(data) -> dict | None:
    """Secret-free panel summary; None until the first poll answered."""
    if not isinstance(data, EzvizControlsStatus):
        return None
    controls = data.controls
    return {
        "supported": data.supported,
        "ptz": bool(controls and controls.ptz),
        "online": controls.online if controls else None,
        "battery_percent": controls.battery_percent if controls else None,
    }


class EzvizControlsCoordinator(DataUpdateCoordinator):
    """Poll only while the bridge health and camera binding are verified."""

    def __init__(self, hass, entry, client, bridge) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
            name="Vistoda EZVIZ controls",
            update_interval=CONTROLS_INTERVAL,
            config_entry=entry,
        )
        self.client = client
        self.bridge = bridge
        self.alias = entry.data[CONF_ALIAS]

    async def _async_update_data(self) -> EzvizControlsStatus:
        # The bridge coordinator re-verifies the immutable camera binding every
        # minute; a failed check must not let a retargeted alias report here.
        if not getattr(self.bridge, "last_update_success", False):
            raise UpdateFailed("EZVIZ bridge or camera binding is unavailable")
        try:
            status = EzvizControlsStatus(True, await self.client.ezviz_controls(self.alias))
        except EzvizFeatureUnsupportedError:
            status = UNSUPPORTED
        except ReauthRequiredError as error:
            # Home Assistant starts the existing Vistoda reauth flow for this entry.
            raise ConfigEntryAuthFailed("EZVIZ session requires a new login") from error
        except BridgeError as error:
            raise UpdateFailed("EZVIZ controls check failed") from error
        return status

    def async_apply(self, controls: EzvizControls) -> None:
        """Publish the controls the app confirmed after a write."""
        self.async_set_updated_data(EzvizControlsStatus(True, controls))
