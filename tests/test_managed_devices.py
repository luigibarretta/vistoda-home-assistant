"""Managed multi-device discovery contracts."""

import pytest

from custom_components.media_bridge.ezviz_binding import CONF_EZVIZ_SOURCE_ID
from custom_components.media_bridge.managed_devices import discovered_devices


def test_ezviz_devices_keep_unique_physical_sources() -> None:
    devices = discovered_devices(
        {
            "devices": [
                {"alias": "front", "source_id": "ABC123:1"},
                {"alias": "garage", "source_id": "XYZ789:2"},
            ]
        }
    )
    assert devices == [
        {"alias": "front", CONF_EZVIZ_SOURCE_ID: "ABC123:1"},
        {"alias": "garage", CONF_EZVIZ_SOURCE_ID: "XYZ789:2"},
    ]


@pytest.mark.parametrize(
    "devices",
    [
        [{"alias": "front", "source_id": "ABC123:1"}, {"alias": "back", "source_id": "ABC123:1"}],
        [{"alias": "front", "source_id": "../camera:1"}],
        [{"alias": "front", "source_id": "ABC123:1", "device_id": "42"}],
    ],
)
def test_invalid_or_ambiguous_source_id_fails_closed(devices) -> None:
    with pytest.raises(ValueError):
        discovered_devices({"devices": devices})
