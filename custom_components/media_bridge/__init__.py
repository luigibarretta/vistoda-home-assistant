"""Vistoda integration setup."""

import voluptuous as vol
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
from .ezviz_alarm_listener import EzvizAlarmListener
from .ezviz_controls import EzvizControlsCoordinator
from .ezviz_media import EzvizMediaCoordinator
from .local import BlinkAdapterCoordinator
from .ring_event_listener import RingEventListener
from .ring_history import RingHistoryManager
from .ring_status import RingStatusCoordinator
from .runtime import BridgeRuntime, MediaBridgeConfigEntry, entry_runtime

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


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Load optional secret bootstrap tokens for zero-copy discovery."""
    from .apple_config_view import async_register as async_register_apple_config
    from .apple_oauth_view import async_register as async_register_apple_oauth
    from .ezviz_alarm_api import async_register as async_register_ezviz_alarms
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
    async_register_ezviz_alarms(hass)
    async_register_services(hass)
    async_register_websocket(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: MediaBridgeConfigEntry) -> bool:
    """Create the bounded bridge client and entities."""
    provider = entry.data[CONF_PROVIDER]
    if provider == PROVIDER_BLINK:
        client = None
        coordinator = BlinkAdapterCoordinator(hass, entry)
    else:
        client = BridgeClient(
            async_get_clientsession(hass),
            entry.data[CONF_URL],
            entry.data[CONF_API_TOKEN],
        )
        coordinator = BridgeCoordinator(hass, client, entry, f"Vistoda {provider} bridge")
    await coordinator.async_config_entry_first_refresh()
    if provider == PROVIDER_EZVIZ:
        from homeassistant.helpers.update_coordinator import UpdateFailed

        from .coordinator import async_check_ezviz_binding
        from .ezviz_binding import CONF_EZVIZ_SOURCE_ID

        if CONF_EZVIZ_SOURCE_ID not in entry.data:
            # The first refresh verified an existing pin; a new entry pins it here.
            try:
                await async_check_ezviz_binding(hass, entry, client, bind=True)
            except UpdateFailed as error:
                raise ConfigEntryNotReady("EZVIZ camera identity is unavailable") from error
        from .ezviz_policy import enforce_delegate_policy

        # Before the platforms: the alarm panel follows the corrected option.
        enforce_delegate_policy(hass, entry)
    ring_status = None
    ring_events = None
    ring_history = None
    if provider == PROVIDER_RING and not entry.data.get("ring_camera_account"):
        from .ring_binding import async_bind_native, async_migrate_registry
        from .ring_facade import async_bind_official

        async_migrate_registry(hass, entry)
        ring_status = RingStatusCoordinator(hass, client, entry.data[CONF_ALIAS], entry)
        await ring_status.async_config_entry_first_refresh()
        async_bind_native(hass, entry, ring_status.data)
        async_bind_official(hass, entry)
        ring_history = RingHistoryManager(hass, entry, client, entry.data[CONF_ALIAS])
        await ring_history.async_initialize()
        ring_events = RingEventListener(hass, entry, client, entry.data[CONF_ALIAS], ring_history)
    base_url = hass.config.external_url or hass.config.internal_url
    snapshots = {}
    snapshot_updated_at = {}
    ezviz_alarms = None
    ezviz_media = None
    ezviz_controls = None
    if provider == PROVIDER_EZVIZ:
        ezviz_alarms = EzvizAlarmListener(
            hass, entry, client, entry.data[CONF_ALIAS], verified=True
        )
        # Constructed only: the sensor and binary_sensor platforms start the first
        # (deferred) polls, so setup never awaits these optional app routes.
        ezviz_media = EzvizMediaCoordinator(hass, entry, client, coordinator)
        ezviz_controls = EzvizControlsCoordinator(hass, entry, client, coordinator)
        from .ezviz_identity import async_migrate_registry
        from .ezviz_snapshot_cache import async_load

        async_migrate_registry(hass, entry)
        image, updated_at = await async_load(hass, entry.entry_id)
        if image is not None:
            snapshots[entry.data[CONF_ALIAS]] = image
        if updated_at is not None:
            snapshot_updated_at[entry.data[CONF_ALIAS]] = updated_at
    entry.runtime_data = BridgeRuntime(
        client=client,
        coordinator=coordinator,
        ring_status=ring_status,
        ring_events=ring_events,
        ring_history=ring_history,
        ezviz_alarms=ezviz_alarms,
        ezviz_media=ezviz_media,
        ezviz_controls=ezviz_controls,
        panel_url=f"{base_url.rstrip('/')}/vistoda/{provider}" if base_url else None,
        snapshots=snapshots,
        snapshot_updated_at=snapshot_updated_at,
    )
    if not entry.data.get("ring_camera_account"):
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    if ring_history:
        entry.async_create_background_task(
            hass,
            ring_history.async_warm_provider(),
            f"Vistoda Ring history warmup {entry.entry_id}",
        )
    if ring_events:
        ring_events.start()
    if ezviz_alarms:
        ezviz_alarms.start()
    if provider == PROVIDER_BLINK:
        from .blink_usb_auto_backup import async_setup as async_setup_usb_backup

        async_setup_usb_backup(hass, entry)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: MediaBridgeConfigEntry) -> bool:
    """Unload entities first; listeners stop only once nothing can fail anymore."""
    if not entry.data.get(
        "ring_camera_account"
    ) and not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    runtime = entry_runtime(entry)
    if runtime and runtime.ring_events:
        await runtime.ring_events.stop()
    if runtime and runtime.ezviz_alarms:
        await runtime.ezviz_alarms.stop()
    from .repairs import remove_entry_issues
    from .ring_camera_websocket import async_close_entry

    await async_close_entry(hass, entry.entry_id)
    # Home Assistant drops entry.runtime_data once this returns True.
    # A reload re-evaluates them; outage clocks survive so a lasting outage stays lasting.
    remove_entry_issues(hass, entry.entry_id)
    if entry.data.get(CONF_PROVIDER) == PROVIDER_EZVIZ:
        from .ezviz_core import refresh_core_issue

        refresh_core_issue(hass, exclude_entry_id=entry.entry_id)
    return True


async def async_remove_entry(hass: HomeAssistant, entry: MediaBridgeConfigEntry) -> None:
    """Leave no repair or outage clock behind for a deleted entry."""
    from .repairs import remove_entry_issues

    remove_entry_issues(hass, entry.entry_id, forget=True)
