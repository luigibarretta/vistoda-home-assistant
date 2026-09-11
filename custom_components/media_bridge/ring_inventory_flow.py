"""Turnkey post-enrollment Ring selection using provider-verified aliases."""

import voluptuous as vol

from .const import CONF_ALIAS, CONF_MANAGED_APP, CONF_PROVIDER, CONF_URL, DOMAIN, PROVIDER_RING
from .errors import BridgeError
from .ring_binding import CONF_RING_DEVICE_ID


class RingInventoryFlowMixin:
    async def async_step_ring_device(self, user_input=None):
        """Read real intercoms after enrollment; never invent a provider route."""
        errors = {}
        if not getattr(self, "_ring_candidates", None):
            try:
                inventory = await self._require_client().ring_intercoms()
                candidates = []
                for item in inventory:
                    alias = item["alias"]
                    if alias is None:
                        alias = await self._legacy_intercom_alias(item, len(inventory))
                    if alias is not None and not self._ring_already_configured(
                        alias, item["device_id"]
                    ):
                        candidates.append({**item, "alias": alias})
                self._ring_candidates = candidates
            except BridgeError:
                errors["base"] = "cannot_connect"
            else:
                if not inventory:
                    errors["base"] = "no_intercoms"
                elif not candidates:
                    errors["base"] = "no_routable_intercoms"
        candidates = getattr(self, "_ring_candidates", [])
        # A device already selected from typed Supervisor discovery needs no
        # second picker, but its identity still came from the fresh inventory.
        requested = (user_input or {}).get("device_id") or self._bridge_data.get(
            CONF_RING_DEVICE_ID
        )
        if requested:
            selected = next((item for item in candidates if item["device_id"] == requested), None)
            if selected is not None:
                if self._ring_already_configured(selected["alias"], requested):
                    return self.async_abort(reason="already_configured")
                self._bridge_data.update(
                    {CONF_ALIAS: selected["alias"], CONF_RING_DEVICE_ID: requested}
                )
                self._ring_inventory_complete = True
                if self._bridge_data.get(CONF_MANAGED_APP):
                    self._managed_remaining = [
                        {CONF_ALIAS: item["alias"], CONF_RING_DEVICE_ID: item["device_id"]}
                        for item in candidates
                        if item is not selected
                    ]
                return await self._finish()
            if candidates:
                errors["base"] = "discovered_device_changed"
        schema = (
            vol.Schema(
                {
                    vol.Required("device_id"): vol.In(
                        {
                            item["device_id"]: " · ".join(
                                filter(None, [item["name"], item["location_name"]])
                            )
                            for item in candidates
                        }
                    )
                }
            )
            if candidates
            else vol.Schema({})
        )
        return self.async_show_form(step_id="ring_device", data_schema=schema, errors=errors)

    async def _legacy_intercom_alias(self, item, count):
        """Compatibility for providers whose inventory predates explicit aliases."""
        alias = next(
            (
                device[CONF_ALIAS]
                for device in getattr(self, "_managed_devices", [])
                if device.get(CONF_RING_DEVICE_ID) == item["device_id"]
            ),
            None,
        )
        if alias is None and count == 1:
            alias = self._bridge_data[CONF_ALIAS]
        if alias is None:
            return None
        status = await self._require_client().ring_status(alias)
        return alias if status.device_id == item["device_id"] else None

    def _ring_already_configured(self, alias, device_id):
        return any(
            entry.data.get(CONF_PROVIDER) == PROVIDER_RING
            and entry.data.get(CONF_URL) == self._bridge_data[CONF_URL]
            and (
                entry.data.get(CONF_ALIAS) == alias
                or entry.data.get(CONF_RING_DEVICE_ID) == device_id
            )
            for entry in self.hass.config_entries.async_entries(DOMAIN)
        )
