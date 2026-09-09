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
    template = (frontend / "ring-recording-template.js").read_text(encoding="utf-8")
    storage = (frontend / "recording-storage.js").read_text(encoding="utf-8")
    list_manager = (frontend / "ring-recording-list-manager.js").read_text(encoding="utf-8")
    item = (frontend / "ring-recording-item.js").read_text(encoding="utf-8")
    player = (frontend / "ring-recording-player.js").read_text(encoding="utf-8")
    ezviz = (frontend / "ezviz-view.js").read_text(encoding="utf-8")
    blink = (frontend / "blink-view.js").read_text(encoding="utf-8")
    websocket = Path("custom_components/media_bridge/ring_recording_websocket.py").read_text(
        encoding="utf-8"
    )
    list_ws = Path("custom_components/media_bridge/ring_recording_list_websocket.py").read_text()
    call_ws = Path("custom_components/media_bridge/ring_call_websocket.py").read_text()
    assert 'id="call"' in view and 'id="stop"' not in view
    assert "mdi:phone-hangup" in view and "mdi:microphone-off" in view
    assert ".actions button[hidden] { display:none !important; }" in view
    assert "mdi:lock-open-variant" in controls and "Comando inviato" in controls
    assert all(
        value in archive + template + item
        for value in ("<table>", "Durata", "Pagina", "Riproduci", "Elimina tutte")
    )
    assert "media_bridge/ring/recordings/read" in player
    assert "Chiudi player" in item
    assert ">Chiudi</span>" in player
    assert "this._seekButton(-10)" in player and "this._seekButton(10)" in player
    assert "URL.revokeObjectURL" in player
    assert "window.confirm" in archive
    assert "mdi:information-outline" in item
    assert 'id="view-cards"' in template and 'id="view-rows"' in template
    assert "preferredRecordingView" in archive and "recordingCard" in archive
    assert "Nuova lista" in template and "Aggiungi alle liste" in list_manager
    assert "media_bridge/ring/recording_lists/set_membership" in list_manager
    assert "Percorso file" in storage and "content-copy" in storage
    assert "recordingStorageSummary" in archive
    assert "media_bridge/ring/recordings/read" in websocket
    assert "media_bridge/ring/recordings/delete_all" in websocket
    assert '"lists": lists' in websocket
    assert all(
        f"media_bridge/ring/recording_lists/{command}" in list_ws
        for command in ("create", "delete", "set_membership")
    )
    assert "media_bridge/ring/call/answer" in call_ws
    assert "vistoda_ring_call_answered" in call_ws
    assert "media_bridge/ring/call/answer" in view
    assert "Caricamento snapshot" in ezviz and "mdi:loading" in ezviz
    assert ".loader[hidden] { display:none !important; }" in ezviz
    assert ">Arma</button>" in (blink + (frontend / "blink-view-template.js").read_text())
    assert "Arma fuori casa</button>" not in blink
    recordings = (frontend / "ring-recordings.js").read_text()
    recorder = (frontend / "ring-local-recorder.js").read_text()
    assert all(
        value in recordings
        for value in (
            "Pausa registrazione",
            "Riprendi registrazione",
            "la comunicazione resta attiva",
        )
    )
    assert "this.recorder.pause()" in recorder and "this.recorder.resume()" in recorder


def test_provider_video_archives_use_typed_ha_boundaries_and_signed_media() -> None:
    from pathlib import Path

    component = Path("custom_components/media_bridge")
    frontend = component / "frontend"
    recordings = (frontend / "provider-recordings.js").read_text()
    model = (frontend / "provider-recording-model.js").read_text()
    websocket = (component / "provider_recording_websocket.py").read_text()
    backup = (component / "recording_backup.py").read_text()
    proxy = (component / "provider_recording_proxy.py").read_text()
    inventory = (component / "panel_info.py").read_text()
    assert "media_bridge/ezviz/recordings/create" in websocket
    assert "connection.user.is_admin" in websocket
    assert "provider_recordings()" in websocket
    assert "requires_auth = True" in proxy
    assert 'type: "auth/sign_path"' in recordings
    assert "recordingMediaPath" in model and "cameraRecordings" in model
    assert "duration_seconds" in recordings and "15 secondi" in recordings
    assert "Backup archivio" in recordings and "backup-all" in recordings
    assert "media_bridge/provider/recordings/backup" in backup + recordings
    assert "_is_nfs_mount(BACKUP_MOUNT)" in backup and "MIN_FREE_BYTES" in backup
    assert 'fields[2] in {"nfs", "nfs4"}' in backup
    assert "digest.hexdigest() != manifest[\"sha256\"]" in backup
    assert '"entries": []' in inventory and '"entry_id": entry.entry_id' in inventory
    assert "api_token" not in recordings + model + websocket + proxy
