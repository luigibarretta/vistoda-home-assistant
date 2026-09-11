"""Physical-device routing and authorization regression tests; no external I/O."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from ring_boundary_support import ValidationError, boundary, call

from custom_components.media_bridge.errors import CannotConnectError
from custom_components.media_bridge.ring_access import can_access_entry
from custom_components.media_bridge.ring_binding import (
    async_bind_native,
    device_identifier,
    verified_device_id,
)


@pytest.mark.asyncio
async def test_explicit_second_entry_with_duplicate_alias_opens_only_second_device(monkeypatch):
    env = boundary(monkeypatch)
    env.add_entry("a", "42")
    env.add_entry("b", "43")
    await env.handle(call("b"))
    env.runtimes["a"].client.unlock_ring.assert_not_awaited()
    env.runtimes["b"].client.unlock_ring.assert_awaited_once_with(
        "entrance", expected_device_id="43"
    )
    env.runtimes["a"].ring_history.async_record.assert_not_awaited()
    env.runtimes["b"].ring_history.async_record.assert_awaited_once()


@pytest.mark.asyncio
async def test_offline_b_never_falls_back_to_only_global_official_a(monkeypatch):
    env = boundary(monkeypatch)
    env.add_entry("a", "42")
    env.add_entry("b", "43", online=False)
    env.add_official("a", "42")
    with pytest.raises(ValidationError):
        await env.handle(call("b"))
    env.hass.services.async_call.assert_not_awaited()
    target = env.add_official("b", "43")
    request = call("b")
    await env.handle(request)
    env.hass.services.async_call.assert_awaited_once_with(
        "button", "press", {"entity_id": target}, blocking=True, context=request.context
    )


@pytest.mark.asyncio
async def test_unloaded_second_entry_still_makes_implicit_selection_ambiguous(monkeypatch):
    env = boundary(monkeypatch)
    env.add_entry("a", "42")
    env.add_entry("b", "43", loaded=False)
    for request in (call(), call("b"), call("missing")):
        with pytest.raises(ValidationError):
            await env.handle(request)
    env.runtimes["a"].client.unlock_ring.assert_not_awaited()


@pytest.mark.asyncio
async def test_alias_retarget_and_uncertain_outcome_never_trigger_fallback(monkeypatch):
    env = boundary(monkeypatch)
    entry = env.add_entry("a", "42")
    env.add_official("a", "42")
    entry.data["ring_device_id"] = "43"
    with pytest.raises(ValidationError, match="binding"):
        await env.handle(call("a"))
    env.runtimes["a"].client.unlock_ring.assert_not_awaited()
    entry.data["ring_device_id"] = "42"
    env.runtimes["a"].client.unlock_ring.side_effect = CannotConnectError
    with pytest.raises(ValidationError, match="outcome is unknown"):
        await env.handle(call("a"))
    env.hass.services.async_call.assert_not_awaited()


@pytest.mark.asyncio
async def test_nonprivileged_user_requires_exact_entry_entity_permission(monkeypatch):
    env = boundary(monkeypatch)
    env.add_entry("a", "42")
    env.add_entry("b", "43")
    for key in ("a", "b"):
        env.registry.entities[key] = SimpleNamespace(
            config_entry_id=key,
            platform="media_bridge",
            entity_id=f"button.{key}",
            unique_id=f"ring-{key}-facade-open_door",
            disabled_by=None,
        )
    user = SimpleNamespace(
        is_active=True,
        is_admin=False,
        permissions=SimpleNamespace(
            check_entity=Mock(side_effect=lambda entity, _: entity == "button.a")
        ),
    )
    env.hass.auth.async_get_user.return_value = user
    assert can_access_entry(env.hass, user, "a")
    assert not can_access_entry(env.hass, user, "b", "control")
    with pytest.raises(ValidationError, match="authorized"):
        await env.handle(call("b", "restricted-user"))
    await env.handle(call("a", "restricted-user"))
    env.runtimes["b"].client.unlock_ring.assert_not_awaited()


def test_namespaces_and_persisted_binding_never_follow_display_alias(monkeypatch):
    env = boundary(monkeypatch)
    first = env.add_entry("a", "42")
    second = env.add_entry("b", "43")
    assert device_identifier(first) != device_identifier(second)
    assert verified_device_id(first, SimpleNamespace(device_id="42")) == "42"
    assert not async_bind_native(env.hass, first, SimpleNamespace(device_id="43"))
    env.hass.config_entries.async_update_entry.assert_not_called()
