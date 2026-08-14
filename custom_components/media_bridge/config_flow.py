"""Native config flow for Vistoda private media bridges."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import BridgeClient, normalize_url
from .const import (
    CONF_ALIAS,
    CONF_API_TOKEN,
    CONF_PROVIDER,
    CONF_URL,
    DEFAULT_EZVIZ_ALIAS,
    DEFAULT_RING_ALIAS,
    DOMAIN,
    PROVIDER_EZVIZ,
    PROVIDER_RING,
    PROVIDERS,
)
from .errors import (
    CannotConnectError,
    EnrollmentBusyError,
    EnrollmentExpiredError,
    InvalidBridgeAuthError,
    InvalidOtpError,
    InvalidVendorAuthError,
    RateLimitedError,
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure a bridge without retaining vendor credentials in HA."""

    VERSION = 1

    def __init__(self) -> None:
        self._provider = PROVIDER_EZVIZ
        self._bridge_data: dict[str, str] = {}
        self._client: BridgeClient | None = None
        self._enrollment_id: str | None = None
        self._credentials_error: str | None = None

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Choose the provider-specific Rust bridge."""
        if user_input is not None:
            self._provider = user_input[CONF_PROVIDER]
            return await self.async_step_bridge()
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PROVIDER, default=PROVIDER_EZVIZ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=PROVIDERS,
                            translation_key="provider",
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
        )

    async def async_step_bridge(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Validate the private endpoint and independent API token."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                url = normalize_url(user_input[CONF_URL])
                client = BridgeClient(
                    async_get_clientsession(self.hass), url, user_input[CONF_API_TOKEN]
                )
                await client.validate(self._provider)
            except ValueError:
                errors["base"] = "invalid_url"
            except InvalidBridgeAuthError:
                errors["base"] = "invalid_bridge_auth"
            except CannotConnectError:
                errors["base"] = "cannot_connect"
            else:
                self._bridge_data = {
                    CONF_PROVIDER: self._provider,
                    CONF_URL: url,
                    CONF_API_TOKEN: user_input[CONF_API_TOKEN],
                    CONF_ALIAS: user_input[CONF_ALIAS],
                }
                self._client = client
                if self._provider == PROVIDER_RING:
                    return await self.async_step_ring_credentials()
                return await self._finish()
        return self.async_show_form(
            step_id="bridge",
            data_schema=bridge_schema(self._provider, user_input),
            errors=errors,
        )

    async def async_step_ring_credentials(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Start one explicit Ring password/MFA enrollment."""
        errors: dict[str, str] = {}
        if self._credentials_error:
            errors["base"] = self._credentials_error
            self._credentials_error = None
        if user_input is not None:
            try:
                enrollment = await self._require_client().start_ring_enrollment(
                    user_input["email"], user_input["password"]
                )
            except InvalidVendorAuthError:
                errors["base"] = "invalid_auth"
            except EnrollmentBusyError:
                errors["base"] = "enrollment_busy"
            except RateLimitedError:
                errors["base"] = "rate_limited"
            except CannotConnectError:
                errors["base"] = "cannot_connect"
            else:
                if enrollment.next_step == "complete":
                    return await self._finish()
                self._enrollment_id = enrollment.enrollment_id
                return await self.async_step_otp()
        return self.async_show_form(
            step_id="ring_credentials",
            data_schema=vol.Schema(
                {
                    vol.Required("email"): selector.TextSelector(
                        selector.TextSelectorConfig(type=selector.TextSelectorType.EMAIL)
                    ),
                    vol.Required("password"): selector.TextSelector(
                        selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_otp(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Consume exactly one SMS code."""
        if user_input is not None:
            try:
                await self._require_client().verify_ring_enrollment(
                    self._enrollment_id or "", user_input["code"]
                )
            except InvalidOtpError:
                return await self._restart_credentials("invalid_otp_restart")
            except EnrollmentExpiredError:
                return await self._restart_credentials("enrollment_expired")
            except RateLimitedError:
                return await self._restart_credentials("rate_limited")
            except CannotConnectError:
                return await self._restart_credentials("cannot_connect_restart")
            return await self._finish()
        return self.async_show_form(
            step_id="otp",
            data_schema=vol.Schema(
                {
                    vol.Required("code"): selector.TextSelector(
                        selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
                    )
                }
            ),
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Update only bridge connection data; vendor session remains bridge-owned."""
        entry = self._get_reconfigure_entry()
        provider = entry.data[CONF_PROVIDER]
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                url = normalize_url(user_input[CONF_URL])
                client = BridgeClient(
                    async_get_clientsession(self.hass), url, user_input[CONF_API_TOKEN]
                )
                await client.validate(provider)
            except ValueError:
                errors["base"] = "invalid_url"
            except InvalidBridgeAuthError:
                errors["base"] = "invalid_bridge_auth"
            except CannotConnectError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={
                        **entry.data,
                        CONF_URL: url,
                        CONF_API_TOKEN: user_input[CONF_API_TOKEN],
                        CONF_ALIAS: user_input[CONF_ALIAS],
                    },
                )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=bridge_schema(provider, user_input or entry.data),
            errors=errors,
        )

    async def _restart_credentials(self, reason: str) -> FlowResult:
        self._enrollment_id = None
        self._credentials_error = reason
        return await self.async_step_ring_credentials()

    async def _finish(self) -> FlowResult:
        unique_id = ":".join(
            (
                self._bridge_data[CONF_PROVIDER],
                self._bridge_data[CONF_URL],
                self._bridge_data[CONF_ALIAS],
            )
        )
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()
        provider = self._bridge_data[CONF_PROVIDER].upper()
        return self.async_create_entry(title=f"Vistoda · {provider}", data=self._bridge_data)

    def _require_client(self) -> BridgeClient:
        if self._client is None:
            raise CannotConnectError
        return self._client


def bridge_schema(provider: str, values: dict[str, Any] | None) -> vol.Schema:
    """Build connection fields with provider-specific safe defaults."""
    values = values or {}
    alias = DEFAULT_RING_ALIAS if provider == PROVIDER_RING else DEFAULT_EZVIZ_ALIAS
    return vol.Schema(
        {
            vol.Required(CONF_URL, default=values.get(CONF_URL, "http://")): str,
            vol.Required(
                CONF_API_TOKEN, default=values.get(CONF_API_TOKEN, "")
            ): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
            ),
            vol.Required(CONF_ALIAS, default=values.get(CONF_ALIAS, alias)): str,
        }
    )
