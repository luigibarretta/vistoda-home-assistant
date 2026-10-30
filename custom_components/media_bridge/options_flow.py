"""Native reconnect and network-backup options."""

import voluptuous as vol
from homeassistant import config_entries

from .backup_storage import (
    CONF_BACKUP_STORAGE,
    DEFAULT_BACKUP_STORAGE,
    storage_mount,
    storage_readiness,
)
from .const import (
    CONF_EVENT_ARCHIVE,
    CONF_EVENT_RETENTION_DAYS,
    CONF_PROVIDER,
    PROVIDER_BLINK,
    PROVIDER_EZVIZ,
    PROVIDER_RING,
)

CONF_AUTO_BACKUP = "blink_usb_auto_backup"


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
                        if provider == PROVIDER_BLINK:
                            enabled = user_input.get(CONF_AUTO_BACKUP, False)
                            if enabled and not readiness["ready"]:
                                errors["base"] = readiness["reason"]
                            else:
                                options[CONF_AUTO_BACKUP] = enabled
                        if provider == PROVIDER_EZVIZ:
                            error = _event_archive_options(user_input, readiness, options)
                            if error:
                                errors["base"] = error
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
        if provider == PROVIDER_BLINK:
            schema[
                vol.Optional(
                    CONF_AUTO_BACKUP, default=self.config_entry.options.get(CONF_AUTO_BACKUP, False)
                )
            ] = bool
        if provider == PROVIDER_EZVIZ:
            current = self.config_entry.options
            schema[
                vol.Optional(CONF_EVENT_ARCHIVE, default=current.get(CONF_EVENT_ARCHIVE, False))
            ] = bool
            schema[
                vol.Optional(
                    CONF_EVENT_RETENTION_DAYS,
                    default=current.get(CONF_EVENT_RETENTION_DAYS, 0),
                )
            ] = vol.All(vol.Coerce(int), vol.Range(min=0, max=3650))
        return self.async_show_form(step_id="init", data_schema=vol.Schema(schema), errors=errors)


def _event_archive_options(user_input: dict, readiness: dict, options: dict) -> str | None:
    """Store the event archive options; an error key when they cannot be accepted."""
    enabled = bool(user_input.get(CONF_EVENT_ARCHIVE, False))
    days = int(user_input.get(CONF_EVENT_RETENTION_DAYS, 0))
    if 0 < days < 7:
        return "invalid_retention"
    if enabled and not readiness["ready"]:
        return readiness["reason"]
    options[CONF_EVENT_ARCHIVE] = enabled
    options[CONF_EVENT_RETENTION_DAYS] = days
    return None
