"""Apply Home Assistant entity permissions to Ring's custom API boundaries."""

from functools import wraps
from inspect import iscoroutinefunction

from .const import DOMAIN
from .ring_binding import entity_prefix


def can_access_entry(hass, user, entry_id: str, action: str = "read") -> bool:
    """Use the selected entry's door entity as the Ring access-control resource."""
    from homeassistant.helpers import entity_registry as er

    if user is None or not user.is_active:
        return False
    if user.is_admin:
        return True
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None:
        return False
    unique_id = f"{entity_prefix(entry)}facade-open_door"
    entities = er.async_get(hass).entities.values()
    return any(
        entity.config_entry_id == entry_id
        and entity.platform == DOMAIN
        and entity.unique_id == unique_id
        and entity.disabled_by is None
        and user.permissions.check_entity(entity.entity_id, action)
        for entity in entities
    )


async def async_require_context(hass, context, entry_id: str) -> None:
    """Respect originating users; allow HA-owned automations without a user ID."""
    from homeassistant.exceptions import ServiceValidationError

    if context is None:
        raise ServiceValidationError("Ring control requires a Home Assistant context")
    if context.user_id is None:
        return
    user = await hass.auth.async_get_user(context.user_id)
    if not can_access_entry(hass, user, entry_id, "control"):
        raise ServiceValidationError("Not authorized to control this Ring entrance")


def require_ring_access(action="read"):
    """Reject custom commands before invoking any provider or storage operation."""

    def decorate(func):
        def permitted(hass, connection, msg):
            allowed = can_access_entry(hass, connection.user, msg["entry_id"], action)
            if not allowed:
                connection.send_error(msg["id"], "unauthorized", "Ring access is not permitted")
            return allowed

        if iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapped(hass, connection, msg):
                if permitted(hass, connection, msg):
                    return await func(hass, connection, msg)
                return None

            return async_wrapped

        @wraps(func)
        def wrapped(hass, connection, msg):
            if permitted(hass, connection, msg):
                return func(hass, connection, msg)
            return None

        return wrapped

    return decorate
