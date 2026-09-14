"""Keep the custom integration's local brand asset in release checkouts."""

import struct
from pathlib import Path


def test_local_brand_is_a_real_square_png() -> None:
    image = (
        Path(__file__).resolve().parents[1] / "custom_components/media_bridge/brand/icon.png"
    ).read_bytes()
    assert image[:8] == b"\x89PNG\r\n\x1a\n"
    assert image[12:16] == b"IHDR"
    width, height = struct.unpack(">II", image[16:24])
    assert width == height == 1024
    assert image[-8:-4] == b"IEND"
