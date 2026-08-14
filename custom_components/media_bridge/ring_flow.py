"""Single-use Ring enrollment steps for the Vistoda Config Flow."""

from typing import Any

from homeassistant.data_entry_flow import FlowResult

from .errors import (
    CannotConnectError,
    EnrollmentBusyError,
    EnrollmentExpiredError,
    InvalidOtpError,
    InvalidVendorAuthError,
    RateLimitedError,
)
from .schemas import otp_schema, ring_credentials_schema


class RingEnrollmentMixin:
    """Keep vendor credentials out of the provider-neutral flow state."""

    async def async_step_ring_credentials(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
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
            data_schema=ring_credentials_schema(),
            errors=errors,
        )

    async def async_step_otp(self, user_input: dict[str, Any] | None = None) -> FlowResult:
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
        return self.async_show_form(step_id="otp", data_schema=otp_schema())

    async def _restart_credentials(self, reason: str) -> FlowResult:
        self._enrollment_id = None
        self._credentials_error = reason
        return await self.async_step_ring_credentials()
