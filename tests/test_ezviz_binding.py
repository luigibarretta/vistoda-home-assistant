"""EZVIZ aliases remain pinned to one physical serial/channel source."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from custom_components.media_bridge.errors import CannotConnectError
from custom_components.media_bridge.ezviz_binding import (
    CONF_EZVIZ_SOURCE_ID,
    async_bind_native,
    async_verify_native,
    source_binding,
    valid_source_id,
)


async def test_first_load_pins_the_provider_camera_identity() -> None:
    entry = SimpleNamespace(data={"alias": "front"})
    hass = SimpleNamespace(config_entries=SimpleNamespace(async_update_entry=Mock()))
    client = SimpleNamespace(ezviz_camera_identity=AsyncMock(return_value="ABC123:2"))

    await async_bind_native(hass, entry, client)

    hass.config_entries.async_update_entry.assert_called_once_with(
        entry, data={"alias": "front", CONF_EZVIZ_SOURCE_ID: "ABC123:2"}
    )


async def test_load_rejects_an_alias_retargeted_to_another_camera() -> None:
    entry = SimpleNamespace(data={"alias": "front", CONF_EZVIZ_SOURCE_ID: "ABC123:2"})
    hass = SimpleNamespace(config_entries=SimpleNamespace(async_update_entry=Mock()))
    client = SimpleNamespace(ezviz_camera_identity=AsyncMock(return_value="OTHER:1"))

    with pytest.raises(CannotConnectError):
        await async_bind_native(hass, entry, client)
    hass.config_entries.async_update_entry.assert_not_called()


async def test_operation_rechecks_the_pinned_camera_identity() -> None:
    entry = SimpleNamespace(data={"alias": "front", CONF_EZVIZ_SOURCE_ID: "ABC123:2"})
    client = SimpleNamespace(ezviz_camera_identity=AsyncMock(return_value="ABC123:2"))

    await async_verify_native(entry, client)
    client.ezviz_camera_identity.assert_awaited_once_with("front")


async def test_operation_fails_closed_without_a_matching_pin() -> None:
    client = SimpleNamespace(ezviz_camera_identity=AsyncMock(return_value="OTHER:1"))
    for data in (
        {"alias": "front"},
        {"alias": "front", CONF_EZVIZ_SOURCE_ID: "ABC123:2"},
    ):
        with pytest.raises(CannotConnectError):
            await async_verify_native(SimpleNamespace(data=data), client)


@pytest.mark.parametrize("value", ["", "serial", "serial:0", "serial:257", "../x:1"])
def test_source_identity_is_strict_and_bounded(value) -> None:
    assert not valid_source_id(value)


def test_live_binding_is_opaque_and_stable() -> None:
    assert source_binding("ABC123:2") == source_binding("ABC123:2")
    assert len(source_binding("ABC123:2")) == 64
    assert "ABC123" not in source_binding("ABC123:2")
