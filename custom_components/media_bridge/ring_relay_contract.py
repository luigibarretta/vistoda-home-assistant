"""Pure bounds for the native Vistoda PCMU relay."""

PROTOCOL = "vistoda.pcmu.v1"
CLIENT_FRAME_BYTES = 160
MAX_MESSAGE_BYTES = 2 * 1024
MAX_SESSION_SECONDS = 125


def valid_client_binary(payload: bytes) -> bool:
    """Accept exactly one 20 ms PCMU frame."""
    return len(payload) == CLIENT_FRAME_BYTES


def valid_server_binary(payload: bytes) -> bool:
    """Accept one non-empty bounded Ring RTP payload."""
    return 0 < len(payload) <= MAX_MESSAGE_BYTES


def valid_text(payload: str) -> bool:
    """Keep control messages bounded without interpreting bridge state."""
    return len(payload.encode("utf-8")) <= MAX_MESSAGE_BYTES
