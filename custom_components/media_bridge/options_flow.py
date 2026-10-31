"""Native reconnect, network-backup and SceneTrove link options."""

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector

from .backup_storage import (
    CONF_BACKUP_STORAGE,
    DEFAULT_BACKUP_STORAGE,
    storage_mount,
    storage_readiness,
)
from .client_helpers import normalize_url
from .const import (
    CLIP_DESTINATIONS,
    CONF_ALIAS,
    CONF_CLIP_DESTINATION,
    CONF_EVENT_ARCHIVE,
    CONF_EVENT_RETENTION_DAYS,
    CONF_PROVIDER,
    CONF_SCENETROVE_DEVICE,
    CONF_SCENETROVE_URL,
    CONF_SHARED_STORAGE,
    PROVIDER_BLINK,
    PROVIDER_EZVIZ,
    PROVIDER_RING,
)
from .managed_devices import SAFE_ALIAS

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
            if provider == PROVIDER_EZVIZ and not errors:
                alias = self.config_entry.data[CONF_ALIAS]
                if (error := _scenetrove_options(user_input, alias, options)) or (error := await self._shared_options(user_input, options)):
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
            # Suggested, not defaulted: Home Assistant drops a cleared optional
            # field, and a default would silently restore the old value.
            alias = self.config_entry.data[CONF_ALIAS]
            for key, suggested in (
                (CONF_SCENETROVE_URL, current.get(CONF_SCENETROVE_URL, "")),
                (CONF_SCENETROVE_DEVICE, current.get(CONF_SCENETROVE_DEVICE, alias)),
            ):
                schema[vol.Optional(key, description={"suggested_value": suggested})] = str
            schema[
                vol.Optional(
                    CONF_CLIP_DESTINATION,
                    default=current.get(CONF_CLIP_DESTINATION, CLIP_DESTINATIONS[0]),
                )
            ] = selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=list(CLIP_DESTINATIONS), translation_key=CONF_CLIP_DESTINATION
                )
            )
            schema[
                vol.Optional(
                    CONF_SHARED_STORAGE,
                    description={"suggested_value": current.get(CONF_SHARED_STORAGE, "")},
                )
            ] = str
        return self.async_show_form(step_id="init", data_schema=vol.Schema(schema), errors=errors)

    async def _shared_options(self, user_input: dict, options: dict) -> str | None:
        """Store the clip destination; sharing needs SceneTrove and ready storage."""
        destination = user_input.get(CONF_CLIP_DESTINATION, CLIP_DESTINATIONS[0])
        storage = user_input.get(CONF_SHARED_STORAGE, "").strip()
        if destination == "shared":
            if not options[CONF_SCENETROVE_URL]:
                return "shared_needs_scenetrove"
            try:
                mount = storage_mount(storage)
            except ValueError:
                return "invalid_storage_name"
            readiness = await self.hass.async_add_executor_job(storage_readiness, mount)
            if not readiness["ready"]:
                return readiness["reason"]
        options[CONF_CLIP_DESTINATION] = destination
        options[CONF_SHARED_STORAGE] = storage
        return None


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


def _scenetrove_options(user_input: dict, alias: str, options: dict) -> str | None:
    """Store the SceneTrove address (empty turns the link off) and device folder."""
    url = user_input.get(CONF_SCENETROVE_URL, "").strip()
    if url:
        try:
            url = normalize_url(url)
        except ValueError:
            return "invalid_scenetrove_url"
    # SceneTrove folders follow the alias rules, so the alias is a valid default;
    # without a link the folder is unused and never blocks the other options.
    device = user_input.get(CONF_SCENETROVE_DEVICE, "").strip() or alias
    if not SAFE_ALIAS.fullmatch(device):
        if url:
            return "invalid_scenetrove_device"
        device = alias
    options[CONF_SCENETROVE_URL] = url
    options[CONF_SCENETROVE_DEVICE] = device
    return None
