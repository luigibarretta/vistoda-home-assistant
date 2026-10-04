"""Vistoda EZVIZ 0.9 encryption, microSD and SD-record client contracts."""

from datetime import date

import pytest

from custom_components.media_bridge.client import BridgeClient
from custom_components.media_bridge.client_ezviz_media import (
    EzvizEncryption,
    EzvizFeatureUnsupportedError,
    EzvizSdRecord,
    EzvizStorage,
    parse_encryption,
    parse_sd_records,
    parse_storage,
)
from custom_components.media_bridge.errors import CannotConnectError, InvalidBridgeAuthError
from tests.test_client import FakeResponse, FakeSession, response


def client(*responses) -> tuple[BridgeClient, FakeSession]:
    session = FakeSession(list(responses))
    return BridgeClient(session, "http://ezviz.local:8787", "x" * 32), session


def test_documents_tolerate_unknown_values() -> None:
    assert parse_encryption({"video_encrypted": True, "key_source": "none"}) == EzvizEncryption(
        True, "none"
    )
    assert parse_encryption({"video_encrypted": "yes", "key_source": "vault"}) == (
        EzvizEncryption(None, None)
    )
    assert parse_storage({"status": "ok", "capacity_mb": 30436}) == EzvizStorage("ok", 30436)
    assert parse_storage({"status": "melted", "capacity_mb": -5}) == EzvizStorage("unknown", None)
    assert parse_storage({"status": "no_card", "capacity_mb": True}) == EzvizStorage(
        "no_card", None
    )


def test_sd_records_are_bounded_sorted_and_typed() -> None:
    records = parse_sd_records(
        {
            "records": [
                {"start": 200, "end": 260, "type": "continuous"},
                {"start": 100, "end": 160, "type": "event"},
                {"start": 300, "end": 200, "type": "event"},
                {"start": "1", "end": 2},
                "garbage",
                {"start": 400, "end": 400, "type": "motion"},
            ]
        }
    )
    assert records == (
        EzvizSdRecord(100, 160, "event"),
        EzvizSdRecord(200, 260, "continuous"),
        EzvizSdRecord(400, 400, "other"),
    )
    many = {"records": [{"start": index, "end": index} for index in range(700)]}
    assert len(parse_sd_records(many)) == 500
    with pytest.raises(CannotConnectError):
        parse_sd_records({"records": "none"})


async def test_routes_are_authenticated_and_404_means_unsupported() -> None:
    api, session = client(
        response(200, {"video_encrypted": False, "key_source": "cloud"}),
        response(200, {"status": "unformatted"}),
        response(200, {"records": [{"start": 1, "end": 2, "type": "event"}]}),
        FakeResponse(404, b'{"error":"not_found"}'),
        FakeResponse(401, b""),
        FakeResponse(200, b"[]"),
    )
    assert await api.ezviz_encryption("front door") == EzvizEncryption(False, "cloud")
    assert await api.ezviz_storage("front door") == EzvizStorage("unformatted", None)
    records = await api.ezviz_sd_records("front door", date(2026, 10, 4))
    assert records == (EzvizSdRecord(1, 2, "event"),)
    method, url, options = session.requests[2]
    assert (method, url) == ("GET", "http://ezviz.local:8787/v1/cameras/front%20door/sd-records")
    assert options["params"] == {"date": "2026-10-04"}
    assert options["headers"]["Authorization"] == f"Bearer {'x' * 32}"
    assert session.requests[0][1].endswith("/v1/cameras/front%20door/encryption")
    assert session.requests[1][1].endswith("/v1/cameras/front%20door/storage")
    with pytest.raises(EzvizFeatureUnsupportedError):
        await api.ezviz_storage("front door")
    with pytest.raises(InvalidBridgeAuthError):
        await api.ezviz_encryption("front door")
    with pytest.raises(CannotConnectError):
        await api.ezviz_storage("front door")
