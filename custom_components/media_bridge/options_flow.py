"""Native reconnect and network-backup options."""

import voluptuous as vol
from homeassistant import config_entries

from .backup_storage import (
    CONF_BACKUP_STORAGE,
    DEFAULT_BACKUP_STORAGE,
    storage_mount,
    storage_readiness,
)
from .const import CONF_PROVIDER, PROVIDER_BLINK, PROVIDER_EZVIZ, PROVIDER_RING


class VistodaOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        provider = self.config_entry.data[CONF_PROVIDER]
        errors = {}
        supports_backup = provider in {PROVIDER_BLINK, PROVIDER_EZVIZ}
        if user_input is not None:
            options = dict(self.config_entry.options)
            if supports_backup:
                try:
                    mount = storage_mount(user_input[CONF_BACKUP_STORAGE])
                except ValueError:
                    errors["base"] = "invalid_storage_name"
                else:
                    readiness = await self.hass.async_add_executor_job(storage_readiness, mount)
                    previous = self.config_entry.options.get(
                        CONF_BACKUP_STORAGE, DEFAULT_BACKUP_STORAGE
                    )
                    if not readiness["ready"] and user_input[CONF_BACKUP_STORAGE] != previous:
                        errors["base"] = readiness["reason"]
                    else:
                        options[CONF_BACKUP_STORAGE] = user_input[CONF_BACKUP_STORAGE]
            if not errors:
                if user_input.get("reconnect_account") and provider in {
                    PROVIDER_RING,
                    PROVIDER_EZVIZ,
                }:
                    self.config_entry.async_start_reauth(self.hass)
                return self.async_create_entry(title="", data=options)
        schema = {}
        if supports_backup:
            schema[
                vol.Required(
                    CONF_BACKUP_STORAGE,
                    default=self.config_entry.options.get(
                        CONF_BACKUP_STORAGE, DEFAULT_BACKUP_STORAGE
                    ),
                )
            ] = str
        if provider in {PROVIDER_RING, PROVIDER_EZVIZ}:
            schema[vol.Optional("reconnect_account", default=False)] = bool
        return self.async_show_form(step_id="init", data_schema=vol.Schema(schema), errors=errors)
