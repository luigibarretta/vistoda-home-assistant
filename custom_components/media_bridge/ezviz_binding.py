"""Persistent physical-camera binding for EZVIZ entries."""

import hashlib
import re

from .const import CONF_ALIAS
from .errors import CannotConnectError

CONF_EZVIZ_SOURCE_ID = "ezviz_source_id"
SOURCE_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}:(?:[1-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-6])$")


def valid_source_id(value) -> bool:
    """Accept only a serial and bounded channel emitted by the local provider."""
    return isinstance(value, str) and len(value) <= 80 and SOURCE_ID.fullmatch(value) is not None


def source_binding(value: str) -> str:
    """Return the opaque immutable token carried by cached live-stream URLs."""
    if not valid_source_id(value):
        raise CannotConnectError
    return hashlib.sha256(value.encode()).hexdigest()


async def async_bind_native(hass, entry, client) -> None:
    """Pin the alias to its camera source and reject silent retargeting."""
    actual = await client.ezviz_camera_identity(entry.data[CONF_ALIAS])
    expected = entry.data.get(CONF_EZVIZ_SOURCE_ID)
    if expected is None:
        hass.config_entries.async_update_entry(
            entry, data={**entry.data, CONF_EZVIZ_SOURCE_ID: actual}
        )
        return
    if expected != actual or not valid_source_id(expected):
        raise CannotConnectError


async def async_verify_native(entry, client) -> None:
    """Fail closed when a configured alias no longer names its pinned camera."""
    expected = entry.data.get(CONF_EZVIZ_SOURCE_ID)
    if not valid_source_id(expected):
        raise CannotConnectError
    if await client.ezviz_camera_identity(entry.data[CONF_ALIAS]) != expected:
        raise CannotConnectError
