"""Tests for the temporary upstream Ring push hardening."""

from types import SimpleNamespace

from custom_components.media_bridge import ring_push_guard


class FakeClient:
    decrypt_arguments = None

    @staticmethod
    def _decrypt_raw_data(credentials, crypto_key, salt, raw_data):
        FakeClient.decrypt_arguments = (credentials, crypto_key, salt, raw_data)
        return b"decoded"

    def _app_data_by_key(self, _message, key, _do_not_raise=False):
        return {
            "crypto-key": "p256ecdsa=peer; dh=abc",
            "encryption": "salt=de",
            "subtype": "application",
        }[key]

    def _handle_data_message(self, _message):
        raise ValueError("synthetic malformed payload")


def test_webpush_header_values_are_named_and_padded() -> None:
    assert ring_push_guard._header_value("p256ecdsa=peer; dh=abc", "dh") == "abc"
    assert ring_push_guard._header_value("salt=de", "salt") == "de"
    assert ring_push_guard._padded("abc") == "abc="
    assert ring_push_guard._padded("de") == "de=="


def test_guard_is_idempotent_and_keeps_malformed_push_local(monkeypatch) -> None:
    module = SimpleNamespace(FcmPushClient=FakeClient)
    monkeypatch.setattr(ring_push_guard, "import_module", lambda _name: module)
    assert ring_push_guard.install_ring_push_guard()
    first_handle = FakeClient._handle_data_message
    assert ring_push_guard.install_ring_push_guard()
    assert FakeClient._handle_data_message is first_handle

    client = FakeClient()
    assert client._app_data_by_key(None, "crypto-key") == "dh=abc"
    assert client._app_data_by_key(None, "encryption") == "salt=de"
    assert FakeClient._decrypt_raw_data({}, "abc", "de", b"raw") == b"decoded"
    assert FakeClient.decrypt_arguments == ({}, "abc=", "de==", b"raw")
    assert client._handle_data_message(SimpleNamespace(persistent_id="test")) is None
