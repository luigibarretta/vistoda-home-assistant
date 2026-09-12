import { WalnutMicrophone } from "./blink-walnut-microphone.js";
import { findLiveVideo } from "./live-fullscreen.js";
import { copy } from "./panel-copy.js";

// Voice-only companion to the existing HA player. It never replaces the video.
export class BlinkWalnutSession {
  constructor(hass, host, onState) {
    this.hass = hass; this.host = host; this.onState = onState;
    this.generation = 0; this.handle = null; this.capture = null;
    this.microphone = false; this.pending = false; this.supported = false;
    this.speaker = false; this.micRequest = 0; this.closed = true;
  }
  get video() { return findLiveVideo(this.host); }

  async start(alias) {
    const generation = ++this.generation; this.closed = false;
    try {
      const unsubscribe = await this.hass.connection.subscribeMessage(
        (event) => this._event(event, generation).catch(() => this._fail(generation)),
        { type: "blink_live_bridge/walnut/subscribe", alias });
      if (generation !== this.generation) { await unsubscribe(); return; }
      this.unsubscribe = unsubscribe;
      this.ping = setInterval(() => this._control("ping").catch(() => this._fail(generation)), 8000);
      this.watch = setInterval(() => {
        if (this.capture && this.video !== this.mutedVideo) {
          this._disableMicrophone(copy(this, "Player audio cambiato: riattiva il microfono"));
        }
        this._state();
      }, 250);
      this.visibility = () => { if (document.hidden) this._disableMicrophone(); };
      document.addEventListener("visibilitychange", this.visibility);
    } catch { await this._fail(generation); }
  }

  async _event(event, generation) {
    if (generation !== this.generation) return;
    if (event.type === "ready") this.handle = event.session_id;
    else if (event.type === "audio_offer") {
      this.sentFrames = Number.isSafeInteger(event.sent_frames) ? event.sent_frames : 0;
      this.supported = event.connected === true && event.supported === true;
      if (!this.supported && this.capture) await this._disableMicrophone();
    } else if (event.type === "microphone") {
      if (event.request_id !== this.micRequest) return;
      const ack = this.micAck; this.micAck = null;
      if (event.enabled === true) ack?.resolve();
      else {
        ack?.reject(new Error(copy(this, "Microfono non disponibile")));
        this._releaseCapture();
        this.message = copy(this, "Microfono fermato: connessione lenta o sessione occupata");
      }
    } else if (["error", "closed"].includes(event.type)) {
      await this._fail(generation); return;
    }
    this._state();
  }

  async toggleSpeaker() {
    const video = this.video; if (!video) return;
    this.speaker = !this.speaker;
    if (this.capture) this.restoreMuted = !this.speaker;
    else {
      video.muted = !this.speaker;
      if (this.speaker) { try { await video.play(); } catch { video.muted = true; this.speaker = false; } }
    }
    this._state();
  }

  async toggleMicrophone() {
    if (this.pending || !this.handle || !this.supported || !this.video) return;
    if (this.microphone) return this._disableMicrophone();
    const generation = this.generation;
    this.pending = true; this.message = "";
    this.mutedVideo = this.video; this.restoreMuted = this.mutedVideo.muted;
    this.enforceMute = () => { if (this.capture && this.mutedVideo && !this.mutedVideo.muted) this.mutedVideo.muted = true; };
    this.mutedVideo.addEventListener("volumechange", this.enforceMute);
    this._state();
    const capture = new WalnutMicrophone(this, (data) => {
      if (generation !== this.generation || this.capture !== capture || document.hidden ||
          this.video !== this.mutedVideo || !this.mutedVideo?.muted) {
        throw new Error(copy(this, "Player audio cambiato: riattiva il microfono"));
      }
      return this._control("pcm", { data });
    },
      (error) => { if (generation === this.generation && this.capture === capture) this._disableMicrophone(error.message); });
    this.capture = capture;
    try {
      if (!await capture.prepare() || generation !== this.generation || this.capture !== capture) {
        capture.stop(); return;
      }
      if (this.video !== this.mutedVideo) throw new Error(copy(this, "Player audio cambiato: riattiva il microfono"));
      this.enforceMute();
      if (!this.mutedVideo.muted) throw new Error(copy(this, "Impossibile sospendere l’ascolto"));
      const requestId = this._nextRequest();
      const acknowledged = new Promise((resolve, reject) => { this.micAck = { resolve, reject }; });
      let timeout;
      try {
        await Promise.all([this._control("microphone", { enabled: true, request_id: requestId }),
          Promise.race([acknowledged, new Promise((_, reject) => {
            timeout = setTimeout(() => reject(new Error(copy(this, "Attivazione microfono scaduta"))), 2000);
          })])]);
      } finally { clearTimeout(timeout); }
      if (generation !== this.generation || this.capture !== capture) { capture.stop(); return; }
      if (this.video !== this.mutedVideo) throw new Error(copy(this, "Player audio cambiato: riattiva il microfono"));
      this.enforceMute();
      if (!this.mutedVideo.muted) throw new Error(copy(this, "Impossibile sospendere l’ascolto"));
      capture.enable(); this.microphone = true;
    } catch (error) {
      capture.stop();
      if (generation !== this.generation || this.capture !== capture) return;
      await this._disableMicrophone(error.message);
    } finally { if (generation === this.generation && this.capture === capture) { this.pending = false; this._state(); } }
  }

  _releaseCapture() {
    this.capture?.stop(); this.capture = null; this.microphone = false; this.pending = false;
    this.micAck?.reject(new Error(copy(this, "Microfono disattivato"))); this.micAck = null;
    if (this.mutedVideo) {
      this.mutedVideo.removeEventListener("volumechange", this.enforceMute);
      this.mutedVideo.muted = this.restoreMuted;
      this.mutedVideo = null;
    }
  }

  async _disableMicrophone(message) {
    const hadCapture = Boolean(this.capture); this._releaseCapture();
    this.message = message || ""; this._state();
    if (hadCapture && this.handle) {
      await this._control("microphone", { enabled: false, request_id: this._nextRequest() })
        .catch(() => this._fail(this.generation));
    }
  }
  _nextRequest() { this.micRequest = (this.micRequest + 1) >>> 0; return this.micRequest; }
  _state() {
    if (this.closed) return;
    const video = this.video;
    if (!this.capture && video) this.speaker = !video.muted;
    const supported = this.supported && Boolean(this.handle && video);
    this.onState({ microphone: this.microphone, microphonePending: this.pending,
      microphoneSupported: supported, speaker: this.speaker,
      message: this.message || copy(this, this.microphone
        ? "Microfono attivo · ascolto sospeso. Disattiva il microfono per ascoltare."
        : supported ? "Live Blink attivo · microfono disponibile" : "Live Blink attivo · microfono non disponibile") });
  }
  _control(action, extra = {}) {
    if (!this.handle) return Promise.reject(new Error(copy(this, "Sessione Blink non pronta")));
    return this.hass.callWS({ type: "blink_live_bridge/walnut/control", session_id: this.handle, action, ...extra });
  }
  async _fail(generation) {
    if (generation !== this.generation) return;
    await this.stop();
    this.onState({ microphone: false, microphonePending: false, microphoneSupported: false,
      message: copy(this, "Canale microfono non disponibile. Controlla la connessione e riapri il live.") });
  }
  async stop() {
    if (this.closed) return;
    this.closed = true; ++this.generation; this._releaseCapture();
    clearInterval(this.watch); clearInterval(this.ping);
    if (this.visibility) document.removeEventListener("visibilitychange", this.visibility);
    const handle = this.handle; this.handle = null;
    const unsubscribe = this.unsubscribe; this.unsubscribe = null;
    await Promise.race([Promise.allSettled([
      ...(handle ? [this.hass.callWS({ type: "blink_live_bridge/walnut/control", session_id: handle, action: "stop" })] : []),
      ...(unsubscribe ? [Promise.resolve(unsubscribe())] : []),
    ]), new Promise((resolve) => setTimeout(resolve, 3000))]);
  }
}
