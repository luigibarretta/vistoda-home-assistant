"""Supervisor-discovered Vistoda app setup."""

from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.service_info.hassio import HassioServiceInfo

from .const import (
    CONF_ALIAS,
    CONF_API_TOKEN,
    CONF_MANAGED_APP,
    CONF_PROVIDER,
    CONF_URL,
    PROVIDER_EZVIZ,
    PROVIDER_RING,
)
from .errors import CannotConnectError, InvalidBridgeAuthError


class ManagedAppDiscoveryMixin:
    """Adopt a private Supervisor app without user-facing bridge fields."""

    async def async_step_hassio(self, discovery_info: HassioServiceInfo) -> FlowResult:
        config = discovery_info.config
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
            self._client = await self._validated_client(
                self._bridge_data[CONF_URL], self._bridge_data[CONF_API_TOKEN]
            )
        except InvalidBridgeAuthError:
            return self.async_abort(reason="invalid_bridge_auth")
        except (CannotConnectError, ValueError):
            return self.async_abort(reason="cannot_connect")
        await self.async_set_unique_id(self._unique_id())
        self._abort_if_unique_id_configured()
        if provider == PROVIDER_RING:
            return await self.async_step_ring_credentials()
        return await self.async_step_ezviz_credentials()
