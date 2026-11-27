"""Browser-playable MP4 from MPEG-TS recordings, copied packet by packet (no re-encoding).

Browsers cannot play raw MPEG-TS in a <video> tag. Home Assistant already ships PyAV for
its stream component, so the panel converts a recording to MP4 on demand. The index goes
first (`faststart`) so playback starts before the whole file is downloaded.

A recording of a live stream does not start where a player expects: its timestamps are the
live session's clock (it can start "at 18 s"), and it begins in the middle of a group of
pictures, so the video cannot be shown until the next key frame while the audio already runs.
The MP4 therefore starts at the first video key frame, for audio and video alike, from zero.
"""

import io
import tempfile
from fractions import Fraction
from pathlib import Path

MP4_OPTIONS = {"movflags": "faststart"}
MAX_REMUX_BYTES = 192 * 1024 * 1024


def _first_key_frame(incoming, video) -> tuple[Fraction, Fraction] | None:
    """(shown at, decoded at) of the first video key frame, in seconds.

    With B-frames a picture is decoded before it is shown, so the clock starts at the decode time.
    """
    for packet in incoming.demux(video):
        if packet.pts is not None and packet.is_keyframe:
            shown = packet.pts * video.time_base
            return shown, (packet.dts if packet.dts is not None else packet.pts) * video.time_base
    return None


def _wanted(packet, cut: Fraction, state: dict) -> bool:
    """Whether a packet belongs after the first key frame (`state["key"]` tracks the video)."""
    if packet.dts is None or packet.pts is None or packet.size == 0:
        return False
    stream = packet.stream
    if stream.type == "video" and not state["key"]:
        state["key"] = packet.is_keyframe
        if not state["key"]:
            return False
    return packet.pts * stream.time_base >= cut


def _shift(packet, origin: Fraction) -> bool:
    """Make `origin` time zero; False for a packet that would end up before it."""
    offset = round(origin / packet.stream.time_base)
    packet.pts -= offset
    packet.dts -= offset
    return packet.dts >= 0


def ts_to_mp4(source: bytes | Path) -> bytes:
    """Return an MP4 holding the first video and audio track of a TS recording.

    Raises ValueError when the input has no playable video or cannot be read.
    """
    import av

    if isinstance(source, bytes):
        size = len(source)
        handle = io.BytesIO(source)
    else:
        size = source.stat().st_size
        handle = str(source)
    if size > MAX_REMUX_BYTES:
        raise ValueError("recording is too large to convert")
    try:
        with tempfile.TemporaryDirectory(prefix="vistoda-remux-") as scratch:
            target = Path(scratch) / "playback.mp4"
            with av.open(handle, mode="r", format="mpegts") as incoming:
                video = [s for s in incoming.streams if s.type == "video"][:1]
                audio = [s for s in incoming.streams if s.type == "audio"][:1]
                if not video:
                    raise ValueError("recording has no video")
                key = _first_key_frame(incoming, video[0])
                indices = [s.index for s in video + audio]  # Stream objects die with the container.
            if key is None:
                raise ValueError("recording has no key frame")
            cut, origin = key
            if isinstance(handle, io.BytesIO):
                handle.seek(0)
            with av.open(handle, mode="r", format="mpegts") as incoming:
                wanted = [incoming.streams[index] for index in indices]
                with av.open(str(target), mode="w", format="mp4", options=MP4_OPTIONS) as out:
                    mapping = {s.index: out.add_stream_from_template(s) for s in wanted}
                    state = {"key": False}
                    for packet in incoming.demux(*wanted):
                        if not _wanted(packet, cut, state) or not _shift(packet, origin):
                            continue
                        packet.stream = mapping[packet.stream.index]
                        out.mux(packet)
            return target.read_bytes()
    except av.FFmpegError as error:
        raise ValueError("recording could not be converted") from error
