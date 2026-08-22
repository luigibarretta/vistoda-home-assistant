const MAX_BYTES = 8 * 1024 * 1024;
const MIME_TYPES = [
  "audio/webm;codecs=opus",
  "audio/mp4;codecs=mp4a.40.2",
  "audio/mp4",
  "audio/webm",
];

export class RingLocalRecorder {
  constructor(hass, entry, onState, environment = globalThis) {
    this.hass = hass;
    this.entry = entry;
    this.onState = onState;
    this.environment = environment;
    this.chunks = [];
    this.bytes = 0;
    this.startedAt = null;
  }

  get active() { return this.recorder?.state === "recording"; }

  supportedType() {
    const Recorder = this.environment.MediaRecorder;
    if (!Recorder) return null;
    return MIME_TYPES.find((value) => Recorder.isTypeSupported?.(value)) || "";
  }

  async start(remoteStream, localStream, includeMicrophone) {
    if (this.active) return;
    const remoteTrack = remoteStream?.getAudioTracks?.()[0];
    const mimeType = this.supportedType();
    if (!remoteTrack || mimeType === null) throw new Error("Registrazione non supportata");
    const Context = this.environment.AudioContext || this.environment.webkitAudioContext;
    if (!Context) throw new Error("Mix audio non supportato");
    this.context = new Context();
    await this.context.resume?.();
    this.destination = this.context.createMediaStreamDestination();
    this.remoteNode = this.context.createMediaStreamSource(remoteStream);
    this.remoteNode.connect(this.destination);
    this.updateLocal(localStream, includeMicrophone);
    const options = mimeType ? { mimeType, audioBitsPerSecond: 96_000 } : {};
    this.recorder = new this.environment.MediaRecorder(this.destination.stream, options);
    this.chunks = [];
    this.bytes = 0;
    this.startedAt = Math.floor(Date.now() / 1000);
    this.recorder.addEventListener("dataavailable", (event) => this.collect(event.data));
    this.recorder.addEventListener("error", () => this.onState("error"));
    this.recorder.start(1000);
    this.onState("recording");
  }

  updateLocal(stream, includeMicrophone) {
    this.localNode?.disconnect();
    this.localNode = null;
    if (!this.context || !includeMicrophone || !stream?.getAudioTracks?.().length) return;
    this.localNode = this.context.createMediaStreamSource(stream);
    this.localNode.connect(this.destination);
  }

  collect(blob) {
    if (!blob?.size) return;
    if (this.bytes + blob.size > MAX_BYTES) {
      this.onState("too_large");
      this.stop(false);
      return;
    }
    this.bytes += blob.size;
    this.chunks.push(blob);
  }

  stop(save = true) {
    if (!this.recorder || this.recorder.state === "inactive") return Promise.resolve(null);
    if (this.stopping) return this.stopping;
    this.stopping = new Promise((resolve) => {
      this.recorder.addEventListener("stop", async () => {
        const type = this.recorder.mimeType || this.chunks[0]?.type || "audio/webm";
        const blob = new Blob(this.chunks, { type });
        const startedAt = this.startedAt;
        await this.cleanup();
        if (!save || blob.size < 128 || !startedAt) return resolve(null);
        try {
          this.onState("uploading");
          const result = await this.upload(blob, startedAt);
          this.onState("saved", result);
          resolve(result);
        } catch (_error) {
          this.onState("upload_failed");
          resolve(null);
        }
      }, { once: true });
      this.recorder.stop();
    }).finally(() => { this.stopping = null; });
    return this.stopping;
  }

  async upload(blob, startedAt) {
    const bytes = new Uint8Array(await blob.arrayBuffer());
    if (bytes.length > MAX_BYTES) throw new Error("Registrazione troppo grande");
    return this.hass.callWS({
      type: "media_bridge/ring/recordings/upload",
      entry_id: this.entry.entry_id,
      started_at: startedAt,
      ended_at: Math.floor(Date.now() / 1000),
      media_type: blob.type || "audio/webm",
      media_base64: bytesToBase64(bytes),
    });
  }

  async cleanup() {
    this.remoteNode?.disconnect();
    this.localNode?.disconnect();
    this.destination?.stream?.getTracks?.().forEach((track) => track.stop());
    await this.context?.close?.();
    this.recorder = null;
    this.context = null;
    this.destination = null;
    this.remoteNode = null;
    this.localNode = null;
    this.chunks = [];
    this.bytes = 0;
    this.startedAt = null;
  }
}

export function bytesToBase64(bytes) {
  let binary = "";
  for (let offset = 0; offset < bytes.length; offset += 0x8000) {
    binary += String.fromCharCode(...bytes.subarray(offset, offset + 0x8000));
  }
  return btoa(binary);
}
