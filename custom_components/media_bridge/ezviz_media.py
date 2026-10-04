"""Ten-minute EZVIZ encryption and microSD status shared by entities and panel."""

import logging
from dataclasses import dataclass
from datetime import timedelta

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client_ezviz_media import EzvizEncryption, EzvizFeatureUnsupportedError, EzvizStorage
from .const import CONF_ALIAS
from .errors import BridgeError

_LOGGER = logging.getLogger(__name__)
# The Vistoda EZVIZ app caches both documents for ten minutes as well.
MEDIA_INTERVAL = timedelta(minutes=10)
PROBLEM_STATUSES = frozenset({"no_card", "unformatted", "error"})
MICROSD_SUFFIX = "microsd"
MICROSD_PROBLEM_SUFFIX = "microsd-problem"


@dataclass(frozen=True, slots=True)
class EzvizMediaStatus:
    """None marks a route the installed app does not offer yet."""

    encryption: EzvizEncryption | None
    storage: EzvizStorage | None


def storage_of(data) -> EzvizStorage | None:
    return getattr(data, "storage", None)


def reports_storage(data) -> bool:
    return storage_of(data) is not None


def media_payload(data) -> dict | None:
    """Secret-free panel view of the last successful poll."""
    if not isinstance(data, EzvizMediaStatus):
        return None
    encryption, storage = data.encryption, data.storage
    return {
        "encryption": None
        if encryption is None
        else {"video_encrypted": encryption.video_encrypted, "key_source": encryption.key_source},
        "storage": None
        if storage is None
        else {"status": storage.status, "capacity_mb": storage.capacity_mb},
    }


class EzvizMediaCoordinator(DataUpdateCoordinator):
    """Poll the app only while the bridge health and camera binding are verified."""

    def __init__(self, hass, entry, client, bridge) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
            name="Vistoda EZVIZ media status",
            update_interval=MEDIA_INTERVAL,
            config_entry=entry,
        )
        self.client = client
        self.bridge = bridge
        self.alias = entry.data[CONF_ALIAS]

    async def _optional(self, read):
        try:
            return await read(self.alias)
        except EzvizFeatureUnsupportedError:
            return None

    async def _async_update_data(self) -> EzvizMediaStatus:
        # The bridge coordinator re-verifies the immutable camera binding every
        # minute; a failed check must not let a retargeted alias report here.
        if not getattr(self.bridge, "last_update_success", False):
            raise UpdateFailed("EZVIZ bridge or camera binding is unavailable")
        try:
            return EzvizMediaStatus(
                encryption=await self._optional(self.client.ezviz_encryption),
                storage=await self._optional(self.client.ezviz_storage),
            )
        except BridgeError as error:
            raise UpdateFailed("EZVIZ media status check failed") from error
