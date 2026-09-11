"""Supervisor-discovered Vistoda app setup."""

import voluptuous as vol
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.service_info.hassio import HassioServiceInfo

from .client_helpers import normalize_url
from .const import (
    CONF_ALIAS,
    CONF_API_TOKEN,
    CONF_MANAGED_APP,
    CONF_PROVIDER,
    CONF_URL,
    DOMAIN,
    PROVIDER_EZVIZ,
    PROVIDER_RING,
)
from .errors import CannotConnectError, InvalidBridgeAuthError
from .ezviz_binding import CONF_EZVIZ_SOURCE_ID
from .managed_devices import discovered_devices
from .ring_binding import CONF_RING_DEVICE_ID


class ManagedAppDiscoveryMixin:
    """Adopt a private Supervisor app without user-facing bridge fields."""

    async def async_step_hassio(self, discovery_info: HassioServiceInfo) -> FlowResult:
        return await self._async_managed_discovery(discovery_info.config)

    async def _async_managed_discovery(self, config, *, authenticated=False) -> FlowResult:
        provider = str(config.get(CONF_PROVIDER, "")).casefold()
        if provider not in {PROVIDER_EZVIZ, PROVIDER_RING}:
            return self.async_abort(reason="unsupported_provider")
        self._provider = provider
        self._bridge_data = {
            CONF_PROVIDER: provider,
            CONF_URL: str(config.get(CONF_URL, "")),
            CONF_API_TOKEN: str(config.get(CONF_API_TOKEN, "")),
            CONF_ALIAS: str(config.get(CONF_ALIAS, "")),
            CONF_MANAGED_APP: True,
        }
        self._set_flow_title()
        try:
            self._bridge_data[CONF_URL] = normalize_url(self._bridge_data[CONF_URL])
            self._managed_devices = discovered_devices(config)
            if self._provider == PROVIDER_RING and any(
                CONF_EZVIZ_SOURCE_ID in device for device in self._managed_devices
            ):
                raise ValueError("EZVIZ identity used for Ring discovery")
            if self._provider == PROVIDER_EZVIZ and any(
                CONF_RING_DEVICE_ID in device for device in self._managed_devices
            ):
                raise ValueError("Ring identity used for EZVIZ discovery")
            self._client = await self._validated_client(
                self._bridge_data[CONF_URL], self._bridge_data[CONF_API_TOKEN]
            )
        except InvalidBridgeAuthError:
            return self.async_abort(reason="invalid_bridge_auth")
        except (CannotConnectError, ValueError):
            return self.async_abort(reason="cannot_connect")
        self._managed_authenticated = authenticated
        self._ring_inventory_complete = authenticated
        self._managed_remaining = []
        return await self.async_step_managed_device()

    async def async_step_managed_device(self, user_input=None) -> FlowResult:
        """Configure every discovered alias through successive native HA flows."""
        available = []
        for device in self._managed_devices:
            self._bridge_data[CONF_ALIAS] = device[CONF_ALIAS]
            try:
                existing = self._existing_provider_entry()
            except ValueError:
                return self.async_abort(reason="discovered_device_changed")
            if existing is None:
                available.append(device)
                continue
            expected = existing.data.get(CONF_RING_DEVICE_ID)
            actual = device.get(CONF_RING_DEVICE_ID)
            if expected and actual and expected != actual:
                return self.async_abort(reason="discovered_device_changed")
            expected_source = existing.data.get(CONF_EZVIZ_SOURCE_ID)
            actual_source = device.get(CONF_EZVIZ_SOURCE_ID)
            if expected_source and actual_source and expected_source != actual_source:
                return self.async_abort(reason="discovered_device_changed")
            updates = {**existing.data, **self._bridge_data, **device}
            changed = self.hass.config_entries.async_update_entry(existing, data=updates)
            if changed:
                await self.hass.config_entries.async_reload(existing.entry_id)
            self._managed_authenticated = True
        if not available:
            return self.async_abort(reason="managed_app_adopted")
        if user_input is None and len(available) > 1:
            return self.async_show_form(
                step_id="managed_device",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_ALIAS): vol.In(
                            {device[CONF_ALIAS]: device[CONF_ALIAS] for device in available}
                        )
                    }
                ),
            )
        alias = user_input[CONF_ALIAS] if user_input else available[0][CONF_ALIAS]
        selected = next((device for device in available if device[CONF_ALIAS] == alias), None)
        if selected is None:
            return self.async_abort(reason="discovered_device_changed")
        self._bridge_data.pop(CONF_RING_DEVICE_ID, None)
        self._bridge_data.update(selected)
        self._managed_remaining = [device for device in available if device is not selected]
        await self.async_set_unique_id(self._unique_id())
        self._abort_if_unique_id_configured()
        if self._managed_authenticated:
            return await self._finish()
        if self._provider == PROVIDER_RING:
            return await self.async_step_ring_credentials()
        return await self.async_step_ezviz_credentials()

    async def _continue_managed_discovery(self):
        """Queue remaining devices only after the selected enrollment succeeds."""
        remaining = getattr(self, "_managed_remaining", [])
        if not remaining:
            return
        self._managed_remaining = []
        config = {
            **self._bridge_data,
            "devices": [
                {
                    "alias": device[CONF_ALIAS],
                    **(
                        {"device_id": device[CONF_RING_DEVICE_ID]}
                        if CONF_RING_DEVICE_ID in device
                        else {}
                    ),
                    **(
                        {"source_id": device[CONF_EZVIZ_SOURCE_ID]}
                        if CONF_EZVIZ_SOURCE_ID in device
                        else {}
                    ),
                }
                for device in remaining
            ],
        }
        config[CONF_ALIAS] = remaining[0][CONF_ALIAS]
        # The internal source is started only by this integration after a successful
        # enrollment. No vendor credential is retained or forwarded to the next flow.
        await self.hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "integration_discovery"},
            data={"managed_continuation": config},
        )

    def _existing_provider_entry(self):
        """An alias is meaningful only within the same authenticated endpoint."""
        matches = [
            entry
            for entry in self.hass.config_entries.async_entries(DOMAIN)
            if entry.data.get(CONF_PROVIDER) == self._provider
            and entry.data.get(CONF_ALIAS) == self._bridge_data[CONF_ALIAS]
            and entry.data.get(CONF_URL) == self._bridge_data[CONF_URL]
        ]
        if len(matches) > 1:
            raise ValueError("ambiguous existing provider entries")
        return matches[0] if matches else None
