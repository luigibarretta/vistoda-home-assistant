"""Archive deletion and panel UX contracts."""

from custom_components.media_bridge.client import BridgeClient


class FakeContent:
    async def iter_chunked(self, _size: int):
        yield b""


class FakeResponse:
    status = 204
    content_length = 0
    content = FakeContent()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None


class FakeSession:
    def __init__(self) -> None:
        self.last_request = None

    async def request(self, method, url, **kwargs):
        self.last_request = (method, url, kwargs)
        return FakeResponse()


async def test_recording_delete_is_idempotent_and_keeps_token_in_header() -> None:
    session = FakeSession()
    client = BridgeClient(session, "http://bridge.local:8775", "x" * 32)
    await client.delete_ring_recording("front entrance", "recording/id")
    method, url, options = session.last_request
    assert method == "DELETE"
    assert url.endswith("/v1/devices/front%20entrance/recordings/recording%2Fid")
    assert options["headers"]["Authorization"] == f"Bearer {'x' * 32}"
    assert "x" * 32 not in url


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
    assert 'id="call"' in view and 'id="stop"' not in view
    assert "mdi:phone-hangup" in view and "mdi:microphone-off" in view
    assert ".actions button[hidden] { display:none !important; }" in view
    assert "mdi:lock-open-variant" in controls and "Comando inviato" in controls
    assert all(value in archive for value in ("<table>", "Durata", "Pagina", "Elimina tutte"))
    assert "window.confirm" in archive
    assert "media_bridge/ring/recordings/delete_all" in websocket
    assert "Caricamento snapshot" in ezviz and "mdi:loading" in ezviz
    assert ".loader[hidden] { display:none !important; }" in ezviz
    assert ">Arma</button>" in blink and "Arma fuori casa</button>" not in blink
