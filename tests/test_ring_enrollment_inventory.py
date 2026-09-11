"""The authenticated inventory client keeps IDs exact and rejects ambiguous aliases."""

from unittest.mock import AsyncMock

import pytest

from custom_components.media_bridge.client import BridgeClient
from custom_components.media_bridge.errors import CannotConnectError


async def test_inventory_reads_the_authenticated_intercom_endpoint():
    client = BridgeClient(None, "http://bridge.local:8787", "x" * 32)
    client._json = AsyncMock(
        return_value={
            "intercoms": [
                {
                    "device_id": "12345678901234567890",
                    "name": "Entrance",
                    "location_name": "Home",
                    "alias": "ring_12345678901234567890",
                    "vendor_secret": "must-be-removed",
                }
            ]
        }
    )
    result = await client.ring_intercoms()
    client._json.assert_awaited_once_with("GET", "/v1/intercoms")
    assert result == [
        {
            "device_id": "12345678901234567890",
            "name": "Entrance",
            "location_name": "Home",
            "alias": "ring_12345678901234567890",
        }
    ]


@pytest.mark.parametrize(
    "items",
    [
        [{"device_id": 123, "name": "Entrance"}],
        [{"device_id": "123", "name": "Entrance", "alias": "../other"}],
        [
            {"device_id": "123", "name": "Entrance", "alias": "same"},
            {"device_id": "456", "name": "Other", "alias": "same"},
        ],
        [{"device_id": "123", "name": "Entrance"}, {"device_id": "123", "name": "Same ID"}],
    ],
)
async def test_inventory_rejects_numeric_ids_and_ambiguous_routes(items):
    client = BridgeClient(None, "http://bridge.local:8787", "x" * 32)
    client._json = AsyncMock(return_value={"intercoms": items})
    with pytest.raises(CannotConnectError):
        await client.ring_intercoms()
