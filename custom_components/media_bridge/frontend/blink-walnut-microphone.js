import { copy } from "./panel-copy.js";
import { claimMicrophone } from "./microphone-coordinator.js";

export class WalnutMicrophone {
  constructor(owner, onFrame, onError) {
    this.owner = owner; this.onFrame = onFrame; this.onError = onError;
    this.closed = false; this.sending = 0; this.active = false; this.activeSince = Infinity;
  }
  async prepare() {
    const Context = globalThis.AudioContext || globalThis.webkitAudioContext;
    if (globalThis.isSecureContext === false) throw new Error(copy(this.owner,
      "Il microfono richiede HTTPS anche sul Wi-Fi di casa. Nelle impostazioni Companion usa un URL interno HTTPS valido."));
    if (!Context || !navigator.mediaDevices?.getUserMedia) throw new Error(copy(this.owner, "Microfono non disponibile: usare HTTPS e un browser aggiornato"));
    this.context = new Context();
    let resumeTimeout;
    try {
      await Promise.race([this.context.resume(), new Promise((_, reject) => {
        resumeTimeout = setTimeout(() => reject(new Error(copy(this.owner, "Dispositivo audio non disponibile"))), 5000);
      })]);
    } finally { clearTimeout(resumeTimeout); }
    // Each capture owns a distinct fallback lease, even when sessions are reused.
    this.lease = await claimMicrophone({ hass: this.owner.hass });
    if (this.closed) { this.lease.release(); return false; }
    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: {
        echoCancellation: true, noiseSuppression: true, autoGainControl: true, channelCount: 1,
      }, video: false });
    } catch (error) {
      const messages = {
        NotAllowedError: "Accesso al microfono negato. Consenti il microfono nelle impostazioni del browser o dell’app Companion.",
        NotFoundError: "Nessun microfono rilevato. Collega o seleziona un dispositivo di ingresso.",
        NotReadableError: "Microfono occupato o non leggibile dal browser. Chiudi le altre app che lo usano e riprova.",
      };
      throw new Error(copy(this.owner, messages[error.name] || "Dispositivo audio non disponibile"));
    }
    if (this.closed) { stream.getTracks().forEach((track) => track.stop()); return false; }
    this.stream = stream;
    this.echoCancellation = stream.getAudioTracks()[0]?.getSettings().echoCancellation === true;
    stream.getAudioTracks()[0].onended = () => this.onError(new Error(copy(this.owner, "Accesso al microfono terminato")));
    await this.context.audioWorklet.addModule(new URL("./blink-pcm-worklet.js", import.meta.url));
    if (this.closed) return false;
    this.node = new AudioWorkletNode(this.context, "blink-pcm-capture");
    this.source = this.context.createMediaStreamSource(stream);
    this.gain = this.context.createGain(); this.gain.gain.value = 0;
    this.source.connect(this.node); this.node.connect(this.gain); this.gain.connect(this.context.destination);
    this.node.port.onmessage = ({ data }) => {
      if (this.closed || !this.active) return;
      if (!Number.isFinite(data.capturedAt) || !(data.samples instanceof ArrayBuffer)
          || data.samples.byteLength !== 1024) { this.onError(new Error(copy(this.owner, "Campione microfono non valido"))); return; }
      if (data.capturedAt - 0.032 < this.activeSince) return;
      const age = this.context.currentTime - data.capturedAt;
      if (age < -0.02 || age > 0.1) return;
      // Drop, never queue or replay stale voice. A transient RTT spike is not a
      // revoked microphone lease. Sustained stalls still hit the send timeout.
      if (this.sending >= 4) return;
      this.sending++;
      const samples = new Int16Array(data.samples); const bytes = new Uint8Array(1024);
      const view = new DataView(bytes.buffer);
      samples.forEach((value, index) => view.setInt16(index * 2, value, true));
      let timeout;
      Promise.race([Promise.resolve().then(() => this.onFrame(btoa(String.fromCharCode(...bytes)))),
        new Promise((_, reject) => { timeout = setTimeout(() => reject(new Error(copy(this.owner, "Invio microfono scaduto"))), 500); })])
        .catch((error) => { if (!this.closed && error?.code !== "busy") this.onError(error); })
        .finally(() => { clearTimeout(timeout); this.sending--; });
    };
    return true;
  }
  enable() { this.activeSince = this.context.currentTime; this.active = true; }
  stop() {
    this.closed = true; this.active = false;
    this.stream?.getTracks().forEach((track) => { track.onended = null; track.stop(); });
    this.node?.disconnect(); this.source?.disconnect(); this.gain?.disconnect();
    this.context?.close().catch(() => {}); this.lease?.release();
  }
}
