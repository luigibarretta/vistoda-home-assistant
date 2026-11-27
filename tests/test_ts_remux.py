"""MPEG-TS recordings become browser-playable MP4 without re-encoding."""

import io
import struct
import sys
from fractions import Fraction
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
from release_flow_support import framework

av = pytest.importorskip("av")

from custom_components.media_bridge import ts_remux  # noqa: E402


def synthetic_ts(tmp_path: Path, audio_tracks: int = 1, *, frames: int = 10) -> Path:
    """A tiny H.264 + AAC transport stream made with PyAV's own encoders."""
    target = tmp_path / "clip.ts"
    with av.open(str(target), mode="w", format="mpegts") as out:
        video = out.add_stream("libx264", rate=10)
        video.width, video.height, video.pix_fmt = 64, 48, "yuv420p"
        video.options = {"x264-params": "keyint=10:min-keyint=10:scenecut=0"}
        video.codec_context.time_base = Fraction(1, 10)  # Real timestamps: 10 frames a second.
        audios = [out.add_stream("aac", rate=16000) for _ in range(audio_tracks)]
        for audio in audios:  # As much audio as there is video (1600 samples per 1/10 s frame).
            for index in range(frames * 1600 // 1024 + 1):
                samples = av.AudioFrame(format="s16", layout="mono", samples=1024)
                samples.sample_rate, samples.pts = 16000, index * 1024
                for plane in samples.planes:
                    plane.update(bytes(plane.buffer_size))
                for packet in audio.encode(samples):
                    out.mux(packet)
            for packet in audio.encode():
                out.mux(packet)
        for index in range(frames):
            frame = av.VideoFrame(64, 48, "yuv420p")
            frame.pts = index
            frame.time_base = Fraction(1, 10)
            for packet in video.encode(frame):
                out.mux(packet)
        for packet in video.encode():
            out.mux(packet)
    return target


def live_cut(source: Path, *, seconds_in: int, drop: int) -> Path:
    """What a recording of a live stream looks like: the session's clock, and a start that
    falls in the middle of a group of pictures (`drop` leading video packets are missing)."""
    target = source.with_name("live.ts")
    with av.open(str(source)) as incoming, av.open(str(target), mode="w", format="mpegts") as out:
        mapping = {s.index: out.add_stream_from_template(s) for s in incoming.streams}
        dropped = 0
        for packet in incoming.demux():
            if packet.dts is None or packet.size == 0:
                continue
            if packet.stream.type == "video" and dropped < drop:
                dropped += 1
                continue
            shift = round(seconds_in / packet.stream.time_base)
            packet.pts, packet.dts = packet.pts + shift, packet.dts + shift
            packet.stream = mapping[packet.stream.index]
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


def first_video_packet(path):
    with av.open(str(path)) as source:
        video = source.streams.video[0]
        packet = next(p for p in source.demux(video) if p.size and p.pts is not None)
        return packet.is_keyframe, float(packet.pts * video.time_base)


def test_a_live_recording_starts_at_zero_on_its_first_key_frame(tmp_path):
    # Like a real one: the clock is the live session's (25 s in) and the first pictures are
    # inter-coded, so the video cannot be shown until the next key frame.
    source = live_cut(synthetic_ts(tmp_path, frames=30), seconds_in=25, drop=3)
    key, shown = first_video_packet(source)
    assert not key and shown >= 25
    data = ts_remux.ts_to_mp4(source)
    with av.open(io.BytesIO(data)) as result:
        video = result.streams.video[0]
        first = next(p for p in result.demux(video) if p.size)
        assert first.is_keyframe
        assert float(first.pts * video.time_base) < 0.5, "must not start 25 s in"
    with av.open(io.BytesIO(data)) as result:
        assert sum(1 for _ in result.decode(video=0)) >= 18  # Every picture after the key frame.
    # Audio and video were cut at the same instant: no audio running ahead of a black picture.
    with av.open(io.BytesIO(data)) as result:
        audio_packets = [p for p in result.demux(result.streams.audio[0]) if p.size]
        assert audio_packets and all(p.pts is not None and p.pts >= 0 for p in audio_packets)
        assert float(audio_packets[0].pts * result.streams.audio[0].time_base) < 0.5


def test_a_recording_without_any_key_frame_is_refused(tmp_path):
    source = live_cut(
        synthetic_ts(tmp_path, frames=8), seconds_in=0, drop=1
    )  # The key frame is gone.
    key, _shown = first_video_packet(source)
    assert not key
    with pytest.raises(ValueError, match="key frame"):
        ts_remux.ts_to_mp4(source)
