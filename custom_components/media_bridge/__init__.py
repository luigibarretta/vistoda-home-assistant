"""Vistoda integration setup."""

from dataclasses import dataclass, field

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import BridgeClient
from .const import (
    CONF_ALIAS,
    CONF_API_TOKEN,
    CONF_DISCOVERY_TOKENS,
    CONF_PROVIDER,
    CONF_URL,
    DOMAIN,
    PLATFORMS,
    PROVIDER_BLINK,
    PROVIDER_EZVIZ,
    PROVIDER_RING,
)
from .coordinator import BridgeCoordinator
from .local import BlinkAdapterCoordinator
from .ring_event_listener import RingEventListener
from .ring_history import RingHistoryManager
from .ring_status import RingStatusCoordinator

CONFIG_SCHEMA = vol.Schema(
    {
        vol.Optional(DOMAIN): vol.Schema(
            {
                vol.Optional(CONF_DISCOVERY_TOKENS, default={}): vol.Schema(
                    {
                        vol.Optional(PROVIDER_EZVIZ): cv.string,
                        vol.Optional(PROVIDER_RING): cv.string,
                    }
                )
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


@dataclass(slots=True)
class BridgeRuntime:
    """Runtime owned by one config entry."""

    client: BridgeClient | None
    coordinator: BridgeCoordinator | BlinkAdapterCoordinator
    ring_status: RingStatusCoordinator | None = None
    ring_events: RingEventListener | None = None
    ring_history: RingHistoryManager | None = None
    panel_url: str | None = None
    snapshots: dict[str, bytes] = field(default_factory=dict)
    snapshot_updated_at: dict[str, str] = field(default_factory=dict)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Load optional secret bootstrap tokens for zero-copy discovery."""
    from .apple_config_view import async_register as async_register_apple_config
    from .apple_oauth_view import async_register as async_register_apple_oauth
    from .panel import async_register as async_register_panel
    from .provider_recording_proxy import async_register as async_register_provider_recording_proxy
    from .ring_audio_proxy import async_register as async_register_ring_audio_proxy
    from .ring_push_guard import install_ring_push_guard
    from .services import async_register as async_register_services
    from .websocket import async_register as async_register_websocket

    install_ring_push_guard()
    settings = config.get(DOMAIN, {})
    hass.data.setdefault(DOMAIN, {})[CONF_DISCOVERY_TOKENS] = settings.get(
        CONF_DISCOVERY_TOKENS, {}
    )
    await async_register_panel(hass)
    async_register_apple_config(hass)
    async_register_apple_oauth(hass)
    async_register_ring_audio_proxy(hass)
    async_register_provider_recording_proxy(hass)
    async_register_services(hass)
    async_register_websocket(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Create the bounded bridge client and entities."""
    provider = entry.data[CONF_PROVIDER]
    if provider == PROVIDER_BLINK:
        client = None
        coordinator = BlinkAdapterCoordinator(hass)
    else:
        client = BridgeClient(
            async_get_clientsession(hass),
            entry.data[CONF_URL],
            entry.data[CONF_API_TOKEN],
        )
        coordinator = BridgeCoordinator(hass, client, entry, f"Vistoda {provider} bridge")
    await coordinator.async_config_entry_first_refresh()
    if provider == PROVIDER_EZVIZ:
        from .errors import BridgeError
        from .ezviz_binding import CONF_EZVIZ_SOURCE_ID, async_bind_native
        from .repairs import update_bridge_issue, update_ezviz_binding_issue

        try:
            if CONF_EZVIZ_SOURCE_ID not in entry.data:
                await async_bind_native(hass, entry, client)
        except BridgeError as error:
            update_bridge_issue(hass, entry, available=True)
            update_ezviz_binding_issue(hass, entry, available=False)
            raise ConfigEntryNotReady("EZVIZ physical camera identity is unavailable") from error
        update_ezviz_binding_issue(hass, entry, available=True)
    ring_status = None
    ring_events = None
    ring_history = None
    if provider == PROVIDER_RING:
        from .ring_binding import async_bind_native, async_migrate_registry
        from .ring_facade import async_bind_official

        async_migrate_registry(hass, entry)
        ring_status = RingStatusCoordinator(hass, client, entry.data[CONF_ALIAS])
        await ring_status.async_config_entry_first_refresh()
        async_bind_native(hass, entry, ring_status.data)
        async_bind_official(hass, entry)
        ring_history = RingHistoryManager(hass, entry, client, entry.data[CONF_ALIAS])
        await ring_history.async_initialize()
        ring_events = RingEventListener(hass, entry, client, entry.data[CONF_ALIAS], ring_history)
    base_url = hass.config.external_url or hass.config.internal_url
    snapshots = {}
    snapshot_updated_at = {}
    if provider == PROVIDER_EZVIZ:
        from .ezviz_identity import async_migrate_registry
        from .ezviz_snapshot_cache import async_load

        async_migrate_registry(hass, entry)
        image, updated_at = await async_load(hass, entry.entry_id)
        if image is not None:
            snapshots[entry.data[CONF_ALIAS]] = image
        if updated_at is not None:
            snapshot_updated_at[entry.data[CONF_ALIAS]] = updated_at
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = BridgeRuntime(
        client=client,
        coordinator=coordinator,
        ring_status=ring_status,
        ring_events=ring_events,
        ring_history=ring_history,
        panel_url=f"{base_url.rstrip('/')}/vistoda/{provider}" if base_url else None,
        snapshots=snapshots,
        snapshot_updated_at=snapshot_updated_at,
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    if ring_history:
        entry.async_create_background_task(
            hass,
            ring_history.async_warm_provider(),
            f"Vistoda Ring history warmup {entry.entry_id}",
        )
    if ring_events:
        ring_events.start()
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload entities and drop the client reference."""
    runtime = hass.data[DOMAIN].get(entry.entry_id)
    if runtime and runtime.ring_events:
        await runtime.ring_events.stop()
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    hass.data[DOMAIN].pop(entry.entry_id, None)
    return True
