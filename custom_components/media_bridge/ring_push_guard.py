"""Temporary hardening for the upstream Ring FCM listener."""

from __future__ import annotations

import logging
from importlib import import_module
from typing import Any

_LOGGER = logging.getLogger(__name__)
_PATCH_MARKER = "_vistoda_ring_push_guard"


def _padded(value: str) -> str:
    """Restore base64url padding stripped from Web Push header values."""
    return value + "=" * (-len(value) % 4)


def _header_value(header: str, name: str) -> str:
    """Select a named Web Push header parameter without retaining peers."""
    for segment in header.split(";"):
        key, separator, value = segment.strip().partition("=")
        if separator and key == name:
            return value.strip()
    bare = header.strip()
    if "=" not in bare.rstrip("="):
        return bare
    raise ValueError(f"missing {name} Web Push parameter")


def install_ring_push_guard() -> bool:
    """Harden the installed FCM client until its upstream fix is released."""
    try:
        module = import_module("firebase_messaging.fcmpushclient")
    except ImportError:
        return False
    client = module.FcmPushClient
    if getattr(client, _PATCH_MARKER, False):
        return True
    if hasattr(module, "_webpush_header_param"):
        return False

    original_decrypt = client._decrypt_raw_data
    original_app_data = client._app_data_by_key
    original_handle = client._handle_data_message

    def decrypt(credentials, crypto_key: str, salt: str, raw_data: bytes) -> bytes:
        return original_decrypt(credentials, _padded(crypto_key), _padded(salt), raw_data)

    def app_data(self, message, key: str, do_not_raise: bool = False) -> str:
        value = original_app_data(self, message, key, do_not_raise)
        if not value:
            return value
        if key == "crypto-key":
            return f"dh={_header_value(value, 'dh')}"
        if key == "encryption":
            return f"salt={_header_value(value, 'salt')}"
        return value

    def handle(self, message) -> Any:
        try:
            return original_handle(self, message)
        except ValueError as error:
            persistent_id = getattr(message, "persistent_id", "unknown")
            _LOGGER.warning(
                "Skipped one malformed Ring push payload (%s, %s)",
                persistent_id,
                type(error).__name__,
            )
            return None

    client._decrypt_raw_data = staticmethod(decrypt)
    client._app_data_by_key = app_data
    client._handle_data_message = handle
    setattr(client, _PATCH_MARKER, True)
    _LOGGER.info("Installed the temporary Vistoda Ring push guard")
    return True
