"""Pure native relay boundary tests."""

from custom_components.media_bridge.ring_relay_contract import (
    CLIENT_FRAME_BYTES,
    MAX_MESSAGE_BYTES,
    MAX_SESSION_SECONDS,
    PROTOCOL,
    valid_client_binary,
    valid_server_binary,
    valid_text,
)


def test_native_relay_contract_is_fixed_and_bounded() -> None:
    assert PROTOCOL == "vistoda.pcmu.v1"
    assert CLIENT_FRAME_BYTES == 160
    assert MAX_MESSAGE_BYTES == 2048
    assert MAX_SESSION_SECONDS == 125


def test_client_accepts_exactly_one_pcmu_frame() -> None:
    assert valid_client_binary(bytes(CLIENT_FRAME_BYTES))
    assert not valid_client_binary(bytes(CLIENT_FRAME_BYTES - 1))
    assert not valid_client_binary(bytes(CLIENT_FRAME_BYTES + 1))


def test_server_and_text_frames_have_hard_limits() -> None:
    assert valid_server_binary(b"x")
    assert valid_server_binary(bytes(MAX_MESSAGE_BYTES))
    assert not valid_server_binary(b"")
    assert not valid_server_binary(bytes(MAX_MESSAGE_BYTES + 1))
    assert valid_text('{"type":"stop"}')
    assert not valid_text("é" * (MAX_MESSAGE_BYTES // 2 + 1))
