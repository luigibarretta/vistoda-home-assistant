"""OAuth callback tests without a Home Assistant runtime."""

from urllib.parse import parse_qs, urlsplit

from custom_components.media_bridge.apple_oauth_contract import (
    CALLBACK_PATH,
    native_callback,
)


def test_same_origin_callback_path_is_stable() -> None:
    assert CALLBACK_PATH == "/api/media_bridge/apple/auth"


def test_authorization_code_is_forwarded_with_state_only() -> None:
    location = native_callback({"code": "one-time-code", "state": "s" * 32, "ignored": "x"})
    assert location is not None
    parts = urlsplit(location)
    assert (parts.scheme, parts.netloc) == ("vistoda", "auth")
    assert parse_qs(parts.query) == {"code": ["one-time-code"], "state": ["s" * 32]}


def test_callback_rejects_ambiguous_or_unbounded_results() -> None:
    state = "s" * 32
    assert native_callback({"state": state}) is None
    assert native_callback({"state": state, "code": "x", "error": "denied"}) is None
    assert native_callback({"state": "short", "code": "x"}) is None
    assert native_callback({"state": state, "code": "x" * 2049}) is None
