// Fragmented MP4 from the authenticated HA relay. No provider URL or credentials.
export class WalnutPlayer {
  constructor(video, onPlaying, onError) {
    this.video = video; this.onPlaying = onPlaying; this.onError = onError;
    this.queue = []; this.queuedBytes = 0; this.initial = new Uint8Array();
    this.closed = false; this.buffer = null;
    const Source = globalThis.MediaSource;
    if (!Source) throw new Error("Questo browser richiede il live compatibile");
    this.source = new Source(); this.url = URL.createObjectURL(this.source);
    this.opened = new Promise((resolve) => this.source.addEventListener("sourceopen", resolve, { once: true }));
    this.video.srcObject = null; this.video.src = this.url; this.video.muted = true;
    this.video.playsInline = true;
    this.playing = () => this.onPlaying();
    this.failed = () => this.onError(new Error("Riproduzione Blink non disponibile"));
    video.addEventListener("playing", this.playing); video.addEventListener("error", this.failed);
  }

  async append(bytes) {
    if (this.closed) return;
    if (!this.buffer) {
      if (this.initial.length + bytes.length > 512 * 1024) throw new Error("Intestazione video Blink troppo grande");
      const initial = new Uint8Array(this.initial.length + bytes.length);
      initial.set(this.initial); initial.set(bytes, this.initial.length); this.initial = initial;
      const codecs = mp4Codecs(initial);
      if (!codecs) return;
      const mime = `video/mp4; codecs="${codecs}"`;
      if (!MediaSource.isTypeSupported(mime)) throw new Error("Codec Blink non supportato dal browser");
      await Promise.race([this.opened, new Promise((_, reject) => setTimeout(() => reject(new Error("Player non pronto")), 5000))]);
      if (this.closed) return;
      this.buffer = this.source.addSourceBuffer(mime);
      this.buffer.addEventListener("updateend", () => this._advance());
      this.buffer.addEventListener("error", this.failed);
      bytes = this.initial; this.initial = new Uint8Array();
    }
    this.queuedBytes += bytes.length;
    if (this.queuedBytes > 2 * 1024 * 1024) throw new Error("Riproduzione troppo lenta; riaprire il live");
    this.queue.push(bytes); this._advance();
  }

  _advance() {
    if (this.closed || !this.buffer || this.buffer.updating) return;
    try {
      const ranges = this.buffer.buffered;
      if (ranges.length) {
        const start = ranges.start(0); const end = ranges.end(ranges.length - 1);
        if (this.video.currentTime < start || end - this.video.currentTime > 1.5) {
          this.video.currentTime = Math.max(start, end - 0.4);
        }
        if (start < end - 12) { this.buffer.remove(start, end - 10); return; }
      }
      const next = this.queue.shift();
      if (next) { this.queuedBytes -= next.length; this.buffer.appendBuffer(next); }
      this.video.play().catch(() => {});
    } catch (error) { this.onError(error); }
  }

  stop() {
    this.closed = true; this.queue = []; this.initial = new Uint8Array();
    this.video.removeEventListener("playing", this.playing);
    this.video.removeEventListener("error", this.failed);
    this.video.pause(); this.video.removeAttribute("src"); this.video.load();
    URL.revokeObjectURL(this.url);
  }
}

export function mp4Codecs(bytes) {
  // Wait for a complete ftyp+moov, not an accidental marker in partial media.
  let offset = 0; let moov = null;
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  while (offset + 8 <= bytes.length) {
    const size = view.getUint32(offset);
    if (size < 8 || size > 512 * 1024) throw new Error("Contenitore video non valido");
    if (offset + size > bytes.length) return null;
    if (String.fromCharCode(...bytes.subarray(offset + 4, offset + 8)) === "moov") {
      moov = bytes.subarray(offset, offset + size); break;
    }
    offset += size;
  }
  if (!moov) return null;
  let avc = null; let audio = false;
  for (let index = 4; index + 8 < moov.length; index++) {
    const type = String.fromCharCode(...moov.subarray(index, index + 4));
    if (type === "avcC" && moov[index + 4] === 1) {
      avc = `avc1.${[...moov.subarray(index + 5, index + 8)].map((v) => v.toString(16).padStart(2, "0")).join("")}`;
    }
    if (type === "mp4a") audio = true;
  }
  if (!avc) throw new Error("Profilo video Blink non riconosciuto");
  return audio ? `${avc},mp4a.40.2` : avc;
}
