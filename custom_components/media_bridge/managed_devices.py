"""Bounded, identity-preserving parsing of Supervisor device discovery."""

import re

from .const import CONF_ALIAS
from .ezviz_binding import CONF_EZVIZ_SOURCE_ID, valid_source_id
from .ring_binding import CONF_RING_DEVICE_ID, valid_device_id

SAFE_ALIAS = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def discovered_devices(config) -> list[dict[str, str]]:
    raw = config.get("devices")
    if raw is None:
        aliases = config.get("aliases", [config.get(CONF_ALIAS)])
        if not isinstance(aliases, list):
            raise ValueError("invalid discovery aliases")
        raw = [{"alias": alias} for alias in aliases]
    if not isinstance(raw, list) or not 1 <= len(raw) <= 64:
        raise ValueError("invalid discovery devices")
    devices, aliases, identifiers, source_ids = [], set(), set(), set()
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("invalid discovered device")
        alias = item.get(CONF_ALIAS)
        device_id = item.get("device_id")
        source_id = item.get("source_id")
        if not isinstance(alias, str) or not SAFE_ALIAS.fullmatch(alias) or alias in aliases:
            raise ValueError("invalid discovered alias")
        if device_id is not None and source_id is not None:
            raise ValueError("ambiguous discovered identity")
        result = {CONF_ALIAS: alias}
        if device_id is not None:
            if not valid_device_id(device_id) or device_id in identifiers:
                raise ValueError("invalid discovered identity")
            result[CONF_RING_DEVICE_ID] = device_id
            identifiers.add(device_id)
        if source_id is not None:
            if not valid_source_id(source_id) or source_id in source_ids:
                raise ValueError("invalid discovered source identity")
            result[CONF_EZVIZ_SOURCE_ID] = source_id
            source_ids.add(source_id)
        aliases.add(alias)
        devices.append(result)
    return devices
