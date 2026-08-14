"""Typed, redacted bridge errors."""


class BridgeError(Exception):
    """Base error without response bodies or credentials."""


class CannotConnectError(BridgeError):
    """Bridge or vendor is temporarily unavailable."""


class InvalidBridgeAuthError(BridgeError):
    """The independent bridge token was rejected."""


class InvalidVendorAuthError(BridgeError):
    """The vendor credentials were rejected."""


class InvalidOtpError(BridgeError):
    """The single-use verification code was rejected."""


class EnrollmentBusyError(BridgeError):
    """Another enrollment owns the bridge slot."""


class EnrollmentExpiredError(BridgeError):
    """The enrollment is expired or consumed."""


class RateLimitedError(BridgeError):
    """A local or vendor rate limit was reached."""
