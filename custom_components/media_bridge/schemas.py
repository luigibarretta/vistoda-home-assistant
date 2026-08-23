"""Reusable Vistoda Config Flow schemas."""

from typing import Any

import voluptuous as vol
from homeassistant.helpers import selector

from .const import (
    CONF_ALIAS,
    CONF_API_TOKEN,
    CONF_PROVIDER,
    CONF_URL,
    DEFAULT_EZVIZ_ALIAS,
    DEFAULT_RING_ALIAS,
    PROVIDER_RING,
    PROVIDERS,
)


def provider_schema() -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_PROVIDER): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=PROVIDERS,
                    translation_key="provider",
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            )
        }
    )


def bridge_schema(provider: str, values: dict[str, Any] | None) -> vol.Schema:
    """Build connection fields with provider-specific safe defaults."""
    values = values or {}
    alias = DEFAULT_RING_ALIAS if provider == PROVIDER_RING else DEFAULT_EZVIZ_ALIAS
    return vol.Schema(
        {
            vol.Required(CONF_URL, default=values.get(CONF_URL, "http://")): str,
            vol.Required(
                CONF_API_TOKEN, default=values.get(CONF_API_TOKEN, "")
            ): password_selector(),
            vol.Required(CONF_ALIAS, default=values.get(CONF_ALIAS, alias)): str,
        }
    )


def discovered_schema() -> vol.Schema:
    return vol.Schema({vol.Required(CONF_API_TOKEN): password_selector()})


def ring_credentials_schema() -> vol.Schema:
    return vol.Schema(
        {
            vol.Required("email"): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.EMAIL)
            ),
            vol.Required("password"): password_selector(),
        }
    )


def ezviz_credentials_schema() -> vol.Schema:
    return vol.Schema(
        {
            vol.Required("account"): str,
            vol.Required("password"): password_selector(),
            vol.Required("api_region", default="eu"): str,
        }
    )


def otp_schema() -> vol.Schema:
    return vol.Schema({vol.Required("code"): password_selector()})


def password_selector() -> selector.TextSelector:
    return selector.TextSelector(
        selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
    )
