import { WalnutPlayer } from "./blink-walnut-player.js";
import { WalnutMicrophone } from "./blink-walnut-microphone.js";
import { copy } from "./panel-copy.js";

export class BlinkWalnutSession {
  constructor(hass, video, onState) {
    this.hass = hass; this.video = video; this.onState = onState;
    this.generation = 0; this.handle = null; this.capture = null;
    this.microphone = false; this.speaker = false; this.supported = false;
    this.streamAec = false; this.pending = false; this.stopping = null;
    this.micRequest = 0;
  }

  async start(alias) {
    const generation = ++this.generation;
    this._state("connecting", copy(this, "Apertura live Blink…"));
    try {
      this.player = new WalnutPlayer(this.video,
        () => { if (generation === this.generation) {
          clearTimeout(this.startTimer); this._state("active");
        } }, (error) => this._fail(error, generation));
      this.startTimer = setTimeout(() => this._fail(new Error("Live audio Blink scaduto"), generation), 25000);
      const unsubscribe = await this.hass.connection.subscribeMessage(
        (event) => this._event(event, generation).catch((error) => this._fail(error, generation)),
        { type: "blink_live_bridge/walnut/subscribe", alias });
      if (generation !== this.generation) { await unsubscribe(); return; }
      this.unsubscribe = unsubscribe;
      this.ping = setInterval(() => this._control("ping").catch(() => {}), 8000);
      this.visibility = () => { if (document.hidden) this._disableMicrophone(); };
      document.addEventListener("visibilitychange", this.visibility);
    } catch (error) { await this._fail(error, generation); }
  }

  async _event(event, generation) {
    if (generation !== this.generation) return;
    if (event.type === "ready") this.handle = event.session_id;
    else if (event.type === "media") {
      if (typeof event.data !== "string" || event.data.length > 87384) throw new Error("Blocco video non valido");
      const bytes = Uint8Array.from(atob(event.data), (char) => char.charCodeAt(0));
      await this.player.append(bytes);
      if (generation === this.generation) await this._control("ack", { sequence: event.sequence });
    } else if (event.type === "audio_offer") {
      this.supported = event.supported === true;
      this.streamAec = event.stream_aec === true;
      this.video.muted = !this.speaker || (this.microphone && !this._duplex());
      if (!this.supported && this.capture) await this._disableMicrophone();
      this._state(this.video.readyState >= 2 ? "active" : "connecting");
    } else if (event.type === "microphone") {
      if (event.request_id !== undefined && event.request_id !== this.micRequest) return;
      const acknowledgement = this.micAck; this.micAck = null;
      if (event.enabled === true) acknowledgement?.resolve();
      else acknowledgement?.reject(new Error(event.message || "Microfono non disponibile"));
      if (event.enabled !== true) {
        this.capture?.stop(); this.capture = null; this.microphone = false; this.pending = false;
        this.video.muted = !this.speaker;
      }
      this._state("active", event.message);
    } else if (["error", "closed"].includes(event.type)) {
      throw new Error(event.message || "Sessione live Blink terminata");
    }
  }

  async toggleSpeaker() {
    this.speaker = !this.speaker;
    this.video.muted = !this.speaker || (this.microphone && !this._duplex());
    if (!this.video.muted) {
      try { await this.video.play(); }
      catch (_error) { this.speaker = false; this.video.muted = true; }
    }
    this._state("active");
  }

  async toggleMicrophone() {
    if (this.pending || !this.handle || !this.supported) return;
    if (this.microphone) return this._disableMicrophone();
    const generation = this.generation;
    this.pending = true; this._state("active");
    const capture = new WalnutMicrophone(this,
      (data) => this._control("pcm", { data }),
      (error) => { if (generation === this.generation && this.capture === capture) {
        this._disableMicrophone(error.message);
      } });
    this.capture = capture;
    try {
      if (!await capture.prepare() || generation !== this.generation || this.capture !== capture) {
        capture.stop(); return;
      }
      this.video.muted = !this.speaker || !this._duplex();
      const requestId = this._nextMicRequest();
      const acknowledged = new Promise((resolve, reject) => { this.micAck = { resolve, reject }; });
      // Attach rejection handling before a provider event can arrive.
      const ready = Promise.race([acknowledged, new Promise((_, reject) =>
        setTimeout(() => reject(new Error("Attivazione microfono scaduta")), 2000))]);
      await Promise.all([ready, this._control("microphone", { enabled: true, request_id: requestId })]);
      if (generation !== this.generation || this.capture !== capture) { capture.stop(); return; }
      this.video.muted = !this.speaker || !this._duplex();
      capture.enable(); this.microphone = true;
    } catch (error) {
      capture.stop();
      if (generation !== this.generation || (this.capture && this.capture !== capture)) return;
      this.capture = null; this.micAck = null;
      await this._control("microphone", { enabled: false, request_id: this._nextMicRequest() }).catch(() => {});
      this.video.muted = !this.speaker;
      this._state("active", error.message);
    } finally {
      if (generation === this.generation) { this.pending = false; this._state("active"); }
    }
  }

  async _disableMicrophone(message) {
    const capture = this.capture; this.capture = null;
    capture?.stop(); this.microphone = false; this.pending = false;
    this.micAck?.reject(new Error("Microfono disattivato")); this.micAck = null;
    this.video.muted = !this.speaker;
    if (capture) await this._control("microphone", { enabled: false, request_id: this._nextMicRequest() }).catch(() => {});
    if (this.player) this._state("active", message);
  }

  _duplex() { return this.streamAec && this.capture?.echoCancellation === true; }
  _nextMicRequest() { this.micRequest = (this.micRequest + 1) >>> 0; return this.micRequest; }

  _state(phase, message) {
    this.onState({ phase, microphone: this.microphone, microphonePending: this.pending,
      microphoneSupported: this.supported, speaker: this.speaker,
      message: message || (this.microphone ? this._duplex()
        ? "Microfono attivo · ascolto simultaneo" : "Microfono attivo · ascolto sospeso per evitare eco"
        : this.supported ? "Live Blink attivo · microfono disponibile" : "Live Blink attivo") });
  }

  _control(action, extra = {}) {
    if (!this.handle) return Promise.reject(new Error("Sessione Blink non pronta"));
    return this.hass.callWS({ type: "blink_live_bridge/walnut/control", session_id: this.handle, action, ...extra });
  }

  async _fail(error, generation) {
    if (generation !== this.generation) return;
    await this.stop(false);
    this.onState({ phase: "fallback", message: error?.message || "Live audio non disponibile" });
  }

  stop(notify = true) {
    if (this.stopping) return this.stopping;
    this.stopping = this._stop(notify).finally(() => { this.stopping = null; });
    return this.stopping;
  }

  async _stop(notify) {
    ++this.generation;
    this.micAck?.reject(new Error("Sessione terminata")); this.micAck = null;
    clearInterval(this.ping); clearTimeout(this.startTimer);
    if (this.visibility) document.removeEventListener("visibilitychange", this.visibility);
    this.capture?.stop(); this.capture = null; this.microphone = false; this.pending = false;
    this.player?.stop(); this.player = null; this.speaker = false;
    const handle = this.handle; this.handle = null;
    const unsubscribe = this.unsubscribe; this.unsubscribe = null;
    if (notify) this._state("idle", copy(this, "Live terminato"));
    await Promise.race([Promise.allSettled([
      ...(handle ? [this.hass.callWS({ type: "blink_live_bridge/walnut/control", session_id: handle, action: "stop" })] : []),
      ...(unsubscribe ? [Promise.resolve(unsubscribe())] : []),
    ]), new Promise((resolve) => setTimeout(resolve, 3000))]);
  }
}
