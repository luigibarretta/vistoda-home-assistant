"""Archive deletion and panel UX contracts."""

from custom_components.media_bridge.client import BridgeClient


class FakeContent:
    def __init__(self, body: bytes = b"") -> None:
        self.body = body

    async def iter_chunked(self, _size: int):
        yield self.body


class FakeResponse:
    def __init__(self, status=204, body=b"", content_type="application/json") -> None:
        self.status = status
        self.content_length = len(body)
        self.content_type = content_type
        self.content = FakeContent(body)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None


class FakeSession:
    def __init__(self, response=None) -> None:
        self.last_request = None
        self.response = response or FakeResponse()

    async def request(self, method, url, **kwargs):
        self.last_request = (method, url, kwargs)
        return self.response


async def test_recording_delete_is_idempotent_and_keeps_token_in_header() -> None:
    session = FakeSession()
    client = BridgeClient(session, "http://bridge.local:8775", "x" * 32)
    await client.delete_ring_recording("front entrance", "recording/id")
    method, url, options = session.last_request
    assert method == "DELETE"
    assert url.endswith("/v1/devices/front%20entrance/recordings/recording%2Fid")
    assert options["headers"]["Authorization"] == f"Bearer {'x' * 32}"
    assert "x" * 32 not in url


async def test_recording_read_is_bounded_and_keeps_token_in_header() -> None:
    media = bytes([0x1A, 0x45, 0xDF, 0xA3]) + b"x" * 124
    session = FakeSession(FakeResponse(200, media, "audio/webm"))
    client = BridgeClient(session, "http://bridge.local:8775", "x" * 32)
    assert await client.read_ring_recording("entrance", "recording/id") == ("audio/webm", media)
    method, url, options = session.last_request
    assert method == "GET"
    assert url.endswith("/v1/devices/entrance/recordings/recording%2Fid")
    assert options["headers"]["Authorization"] == f"Bearer {'x' * 32}"


def test_ring_archive_and_controls_expose_compact_contextual_ux() -> None:
    from pathlib import Path

    frontend = Path("custom_components/media_bridge/frontend")
    view = (frontend / "ring-view.js").read_text(encoding="utf-8")
    controls = (frontend / "ring-controls.js").read_text(encoding="utf-8")
    archive = (frontend / "ring-recording-archive.js").read_text(encoding="utf-8")
    ezviz = (frontend / "ezviz-view.js").read_text(encoding="utf-8")
    blink = (frontend / "blink-view.js").read_text(encoding="utf-8")
    websocket = Path("custom_components/media_bridge/ring_recording_websocket.py").read_text(
        encoding="utf-8"
    )
    call_ws = Path("custom_components/media_bridge/ring_call_websocket.py").read_text()
    assert 'id="call"' in view and 'id="stop"' not in view
    assert "mdi:phone-hangup" in view and "mdi:microphone-off" in view
    assert ".actions button[hidden] { display:none !important; }" in view
    assert "mdi:lock-open-variant" in controls and "Comando inviato" in controls
    assert all(
        value in archive for value in ("<table>", "Durata", "Pagina", "Riproduci", "Elimina tutte")
    )
    assert "media_bridge/ring/recordings/read" in archive
    assert "this._seekButton(-10)" in archive and "this._seekButton(10)" in archive
    assert "URL.revokeObjectURL" in archive
    assert "window.confirm" in archive
    assert "media_bridge/ring/recordings/read" in websocket
    assert "media_bridge/ring/recordings/delete_all" in websocket
    assert "media_bridge/ring/call/answer" in call_ws
    assert "vistoda_ring_call_answered" in call_ws
    assert "media_bridge/ring/call/answer" in view
    assert "Caricamento snapshot" in ezviz and "mdi:loading" in ezviz
    assert ".loader[hidden] { display:none !important; }" in ezviz
    assert ">Arma</button>" in blink and "Arma fuori casa</button>" not in blink
