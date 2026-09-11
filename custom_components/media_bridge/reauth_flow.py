"""Reconnect vendor accounts without replacing the configured device identity."""

from .const import CONF_API_TOKEN, CONF_PROVIDER, CONF_URL, PROVIDER_EZVIZ, PROVIDER_RING
from .errors import CannotConnectError, InvalidBridgeAuthError


class ReauthenticationMixin:
    """Reuse enrollment, keeping credentials in the current request only."""

    async def async_step_reauth(self, entry_data):
        return await self._begin_reauthentication(self._get_reauth_entry())

    async def _begin_reauthentication(self, entry):
        self._provider = entry.data[CONF_PROVIDER]
        if self._provider not in {PROVIDER_RING, PROVIDER_EZVIZ}:
            return self.async_abort(reason="local_adapter")
        self._reauth_entry = entry
        self._bridge_data = dict(entry.data)
        self._client = None
        self._enrollment_id = None
        self._credentials_error = None
        self._set_flow_title()
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                self._client = await self._validated_client(
                    self._bridge_data[CONF_URL], self._bridge_data[CONF_API_TOKEN]
                )
            except InvalidBridgeAuthError:
                errors["base"] = "invalid_bridge_auth"
            except (CannotConnectError, ValueError):
                errors["base"] = "cannot_connect"
            else:
                if self._provider == PROVIDER_RING:
                    return await self.async_step_ring_credentials()
                return await self.async_step_ezviz_credentials()
        return self.async_show_form(
            step_id="reauth_confirm",
            errors=errors,
            description_placeholders={"provider": self._provider.upper()},
        )

    def _finish_reauthentication(self):
        self._enrollment_id = None
        # Enrollment did not alter the endpoint, alias, unique ID or physical binding.
        # Preserve changes made by other flows while this enrollment was open.
        entry = self._reauth_entry
        return self.async_update_reload_and_abort(
            entry,
            data_updates={},
            reason="reauth_successful",
        )
