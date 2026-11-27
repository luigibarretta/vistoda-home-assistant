"""MPEG-TS recordings become browser-playable MP4 without re-encoding."""

import io
import struct
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
from release_flow_support import framework

av = pytest.importorskip("av")

from custom_components.media_bridge import ts_remux  # noqa: E402


def synthetic_ts(tmp_path: Path, audio_tracks: int = 1) -> Path:
    """A tiny H.264 + AAC transport stream made with PyAV's own encoders."""
    target = tmp_path / "clip.ts"
    with av.open(str(target), mode="w", format="mpegts") as out:
        video = out.add_stream("libx264", rate=10)
        video.width, video.height, video.pix_fmt = 64, 48, "yuv420p"
        audios = [out.add_stream("aac", rate=16000) for _ in range(audio_tracks)]
        for index in range(10):
            frame = av.VideoFrame(64, 48, "yuv420p")
            frame.pts = index
            frame.time_base = video.time_base
            for packet in video.encode(frame):
                out.mux(packet)
        for packet in video.encode():
            out.mux(packet)
        for audio in audios:
            samples = av.AudioFrame(format="s16", layout="mono", samples=1024)
            samples.sample_rate, samples.pts = 16000, 0
            for plane in samples.planes:
                plane.update(bytes(plane.buffer_size))
            for packet in audio.encode(samples):
                out.mux(packet)
            for packet in audio.encode():
                out.mux(packet)
    return target


def atoms(data: bytes) -> list[str]:
    found, index = [], 0
    while index + 8 <= len(data):
        size, kind = struct.unpack(">I4s", data[index : index + 8])
        found.append(kind.decode())
        index += size
    return found


def test_conversion_keeps_the_streams_and_puts_the_index_first(tmp_path):
    data = ts_remux.ts_to_mp4(synthetic_ts(tmp_path))
    assert atoms(data).index("moov") < atoms(data).index("mdat")
    with av.open(io.BytesIO(data)) as result:
        assert [s.type for s in result.streams] == ["video", "audio"]
        assert result.streams.video[0].codec_context.name == "h264"
        assert sum(1 for _ in result.decode(video=0)) == 10


def test_only_the_first_audio_track_is_kept_and_bytes_work_too(tmp_path):
    source = synthetic_ts(tmp_path, audio_tracks=2)
    data = ts_remux.ts_to_mp4(source.read_bytes())
    with av.open(io.BytesIO(data)) as result:
        assert len(result.streams.audio) == 1


def test_garbage_and_oversized_input_are_refused(tmp_path, monkeypatch):
    with pytest.raises(ValueError):
        ts_remux.ts_to_mp4(b"not a transport stream" * 200)
    monkeypatch.setattr(ts_remux, "MAX_REMUX_BYTES", 10)
    with pytest.raises(ValueError, match="too large"):
        ts_remux.ts_to_mp4(b"x" * 11)


def playback_module(monkeypatch):
    env = framework(monkeypatch)
    http = ModuleType("homeassistant.components.http")
    http.HomeAssistantView = object
    monkeypatch.setitem(sys.modules, http.__name__, http)
    return env.load("blink_playback")


def request(range_header=None):
    return SimpleNamespace(headers={"Range": range_header} if range_header else {})


def test_whole_file_and_byte_ranges_are_served_for_seeking(monkeypatch):
    module = playback_module(monkeypatch)
    data = bytes(range(100))
    whole = module.mp4_response(request(), data)
    assert whole.status == 200 and whole.body == data
    assert whole.headers["Content-Type"] == "video/mp4"
    part = module.mp4_response(request("bytes=10-19"), data)
    assert part.status == 206 and part.body == data[10:20]
    assert part.headers["Content-Range"] == "bytes 10-19/100"
    assert module.mp4_response(request("bytes=90-"), data).body == data[90:]
    assert module.mp4_response(request("bytes=-5"), data).body == data[-5:]
    assert module.mp4_response(request("bytes=500-"), data).status == 416
    assert module.mp4_response(request("bytes=abc"), data).status == 200
