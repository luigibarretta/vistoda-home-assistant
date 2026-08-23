"""Single-use EZVIZ enrollment steps for managed Vistoda apps."""

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
from .schemas import ezviz_credentials_schema, otp_schema


class EzvizEnrollmentMixin:
    """Enroll EZVIZ without persisting account credentials in Home Assistant."""

    async def async_step_ezviz_credentials(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}
        if self._credentials_error:
            errors["base"] = self._credentials_error
            self._credentials_error = None
        if user_input is not None:
            try:
                enrollment = await self._require_client().start_ezviz_enrollment(
                    user_input["account"],
                    user_input["password"],
                    user_input["api_region"],
                )
            except InvalidVendorAuthError:
                errors["base"] = "ezviz_invalid_auth"
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
                return await self.async_step_ezviz_otp()
        return self.async_show_form(
            step_id="ezviz_credentials",
            data_schema=ezviz_credentials_schema(),
            errors=errors,
        )

    async def async_step_ezviz_otp(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            try:
                await self._require_client().verify_enrollment(
                    self._enrollment_id or "", user_input["code"]
                )
            except InvalidOtpError:
                return await self._restart_ezviz("ezviz_invalid_otp_restart")
            except EnrollmentExpiredError:
                return await self._restart_ezviz("enrollment_expired")
            except RateLimitedError:
                return await self._restart_ezviz("rate_limited")
            except CannotConnectError:
                return await self._restart_ezviz("cannot_connect_restart")
            return await self._finish()
        return self.async_show_form(step_id="ezviz_otp", data_schema=otp_schema())

    async def _restart_ezviz(self, reason: str) -> FlowResult:
        self._enrollment_id = None
        self._credentials_error = reason
        return await self.async_step_ezviz_credentials()
