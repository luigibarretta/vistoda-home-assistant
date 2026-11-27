"""Browser-playable MP4 from MPEG-TS recordings, copied packet by packet (no re-encoding).

Browsers cannot play raw MPEG-TS in a <video> tag. Home Assistant already ships PyAV for
its stream component, so the panel converts a recording to MP4 on demand. The index goes
first (`faststart`) so playback starts before the whole file is downloaded.
"""

import io
import tempfile
from pathlib import Path

MP4_OPTIONS = {"movflags": "faststart"}
MAX_REMUX_BYTES = 192 * 1024 * 1024


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
                wanted = video + audio
                with av.open(str(target), mode="w", format="mp4", options=MP4_OPTIONS) as out:
                    mapping = {s.index: out.add_stream_from_template(s) for s in wanted}
                    for packet in incoming.demux(*wanted):
                        if packet.dts is None or packet.size == 0:
                            continue
                        packet.stream = mapping[packet.stream.index]
                        out.mux(packet)
            return target.read_bytes()
    except av.FFmpegError as error:
        raise ValueError("recording could not be converted") from error
