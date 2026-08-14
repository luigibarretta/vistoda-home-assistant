"""Native Config Flow for local and remote Vistoda providers."""

from __future__ import annotations

from ipaddress import ip_address
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .client import BridgeClient, normalize_url
from .const import (
    CONF_ALIAS,
    CONF_API_TOKEN,
    CONF_DISCOVERY_TOKENS,
    CONF_PROVIDER,
    CONF_URL,
    DEFAULT_BLINK_ALIAS,
    DOMAIN,
    PROVIDER_BLINK,
    PROVIDER_EZVIZ,
    PROVIDER_RING,
)
from .errors import CannotConnectError, InvalidBridgeAuthError
from .local import blink_adapter_available
from .ring_flow import RingEnrollmentMixin
from .schemas import bridge_schema, discovered_schema, provider_schema

REMOTE_PROVIDERS = frozenset({PROVIDER_EZVIZ, PROVIDER_RING})


class ConfigFlow(RingEnrollmentMixin, config_entries.ConfigFlow, domain=DOMAIN):
    """Configure a provider without retaining vendor credentials in HA."""

    VERSION = 1

    def __init__(self) -> None:
        self._provider = PROVIDER_EZVIZ
        self._bridge_data: dict[str, str] = {}
        self._client: BridgeClient | None = None
        self._enrollment_id: str | None = None
        self._credentials_error: str | None = None
        self._discovery_token: str | None = None

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        self._set_flow_title()
        if user_input is not None:
            self._provider = user_input[CONF_PROVIDER]
            if self._provider == PROVIDER_BLINK:
                return await self.async_step_blink()
            return await self.async_step_bridge()
        return self.async_show_form(step_id="user", data_schema=provider_schema())

    async def async_step_blink(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Adopt the loaded Blink relay without a second vendor login."""
        if not blink_adapter_available(self.hass):
            return self.async_abort(reason="blink_not_loaded")
        await self.async_set_unique_id("blink:local")
        self._abort_if_unique_id_configured()
        if user_input is None:
            return self.async_show_form(step_id="blink")
        self._bridge_data = {
            CONF_PROVIDER: PROVIDER_BLINK,
            CONF_ALIAS: DEFAULT_BLINK_ALIAS,
        }
        return await self._finish()

    async def async_step_integration_discovery(self, discovery_info: dict[str, Any]) -> FlowResult:
        """Receive a local adapter discovery initiated by Blink Live Bridge."""
        if discovery_info.get(CONF_PROVIDER) != PROVIDER_BLINK:
            return self.async_abort(reason="unsupported_provider")
        self._provider = PROVIDER_BLINK
        self._set_flow_title()
        return await self.async_step_blink()

    async def async_step_zeroconf(self, discovery_info: ZeroconfServiceInfo) -> FlowResult:
        """Prefill a remote bridge announced on the private LAN."""
        properties = {str(key): str(value) for key, value in discovery_info.properties.items()}
        provider = properties.get(CONF_PROVIDER, "").casefold()
        if provider not in REMOTE_PROVIDERS:
            return self.async_abort(reason="unsupported_provider")
        alias = properties.get(CONF_ALIAS) or (
            "entrance" if provider == PROVIDER_RING else "front-door"
        )
        self._provider = provider
        self._bridge_data = {
            CONF_PROVIDER: provider,
            CONF_URL: service_url(discovery_info.host, discovery_info.port),
            CONF_ALIAS: alias,
        }
        self._discovery_token = (
            self.hass.data.get(DOMAIN, {}).get(CONF_DISCOVERY_TOKENS, {}).get(provider)
        )
        await self.async_set_unique_id(self._unique_id())
        self._abort_if_unique_id_configured()
        self._set_flow_title()
        return await self.async_step_discovery_confirm()

    async def async_step_discovery_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            token = self._discovery_token or user_input.get(CONF_API_TOKEN, "")
            try:
                client = await self._validated_client(self._bridge_data[CONF_URL], token)
            except InvalidBridgeAuthError:
                errors["base"] = "invalid_bridge_auth"
            except CannotConnectError:
                errors["base"] = "cannot_connect"
            else:
                self._bridge_data[CONF_API_TOKEN] = token
                self._client = client
                if self._provider == PROVIDER_RING:
                    return await self.async_step_ring_credentials()
                return await self._finish()
        schema = vol.Schema({}) if self._discovery_token else discovered_schema()
        return self.async_show_form(
            step_id="discovery_confirm",
            data_schema=schema,
            errors=errors,
            description_placeholders={"provider": self._provider.upper()},
        )

    async def async_step_bridge(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                url = normalize_url(user_input[CONF_URL])
                client = await self._validated_client(url, user_input[CONF_API_TOKEN])
            except ValueError:
                errors["base"] = "invalid_url"
            except InvalidBridgeAuthError:
                errors["base"] = "invalid_bridge_auth"
            except CannotConnectError:
                errors["base"] = "cannot_connect"
            else:
                self._bridge_data = {CONF_PROVIDER: self._provider, **user_input, CONF_URL: url}
                self._client = client
                if self._provider == PROVIDER_RING:
                    return await self.async_step_ring_credentials()
                return await self._finish()
        return self.async_show_form(
            step_id="bridge", data_schema=bridge_schema(self._provider, user_input), errors=errors
        )

    async def async_step_reconfigure(self, user_input=None) -> FlowResult:
        entry = self._get_reconfigure_entry()
        provider = entry.data[CONF_PROVIDER]
        self._provider = provider
        self._set_flow_title()
        if provider == PROVIDER_BLINK:
            return self.async_abort(reason="local_adapter")
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                url = normalize_url(user_input[CONF_URL])
                await self._validated_client(url, user_input[CONF_API_TOKEN])
            except ValueError:
                errors["base"] = "invalid_url"
            except InvalidBridgeAuthError:
                errors["base"] = "invalid_bridge_auth"
            except CannotConnectError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_update_reload_and_abort(
                    entry, data_updates={**entry.data, **user_input, CONF_URL: url}
                )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=bridge_schema(provider, user_input or entry.data),
            errors=errors,
        )

    async def _validated_client(self, url: str, token: str) -> BridgeClient:
        client = BridgeClient(async_get_clientsession(self.hass), url, token)
        await client.validate(self._provider)
        return client

    async def _finish(self) -> FlowResult:
        await self.async_set_unique_id(self._unique_id())
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=f"Vistoda · {self._provider.upper()}", data=self._bridge_data
        )

    def _unique_id(self) -> str:
        if self._provider == PROVIDER_BLINK:
            return "blink:local"
        return ":".join(
            (self._provider, self._bridge_data[CONF_URL], self._bridge_data[CONF_ALIAS])
        )

    def _set_flow_title(self) -> None:
        """Supply the title placeholder for manual and discovered flows."""
        name = "Vistoda"
        if self.context.get("source") != config_entries.SOURCE_USER:
            name = f"{name} · {self._provider.upper()}"
        self.context["title_placeholders"] = {"name": name}

    def _require_client(self) -> BridgeClient:
        if self._client is None:
            raise CannotConnectError
        return self._client


def service_url(host: str, port: int) -> str:
    """Render a discovery address without corrupting IPv6 literals."""
    parsed = ip_address(host)
    authority = f"[{parsed}]" if parsed.version == 6 else str(parsed)
    return f"http://{authority}:{port}"
