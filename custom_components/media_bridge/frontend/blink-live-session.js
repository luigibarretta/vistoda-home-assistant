import { copy } from "./panel-copy.js";
import { BlinkLegacyLiveSession } from "./blink-legacy-live-session.js";
import { BlinkWebRtcSession } from "./blink-webrtc-session.js";
import { BlinkWalnutSession } from "./blink-walnut-session.js";

export class BlinkLiveSession {
  constructor(hass, video, legacyHost, onState, factories = {}) {
    this._hass = hass;
    this.video = video;
    this.legacyHost = legacyHost;
    this.onState = onState;
    this.makeWebRtc = factories.webRtc || ((handler) =>
      new BlinkWebRtcSession(this._hass, this.video, handler));
    this.makeLegacy = factories.legacy || (() =>
      new BlinkLegacyLiveSession(this._hass, this.legacyHost));
    this.makeWalnut = factories.walnut || ((handler) =>
      new BlinkWalnutSession(this._hass, this.video, handler));
    this.mode = "idle";
    this.generation = 0;
    this.fallbackUsed = false;
    this.webRtc = null;
    this.walnut = null;
    this.legacy = null;
    this.entityId = null;
    this.stopping = null;
  }

  set hass(value) {
    this._hass = value;
    if (this.webRtc) this.webRtc.hass = value;
    if (this.walnut) this.walnut.hass = value;
    if (this.legacy) this.legacy.hass = value;
  }

  get active() { return ["webrtc", "walnut_audio", "switching", "legacy"].includes(this.mode); }

  async start(alias, entityId, preferredTransport = "walnut") {
    if (this.active) return;
    const generation = ++this.generation;
    this.entityId = entityId;
    this.fallbackUsed = false;
    if (preferredTransport !== "cayuga") {
      this.mode = "walnut_audio";
      this.walnut = this.makeWalnut((state) => {
        if (generation !== this.generation) return;
        if (state.phase === "fallback") {
          this._activateLegacy("automatic", generation).catch(() => {}); return;
        }
        this.onState({ ...state, transport: "walnut_audio", legacyAvailable: false });
      });
      await this.walnut.start(alias);
      return;
    }
    this.mode = "webrtc";
    const webRtc = this.makeWebRtc((state) => this._webRtcState(state, generation));
    this.webRtc = webRtc;
    await webRtc.start(alias);
  }

  async startLegacy() {
    if (this.active || !this.entityId) return;
    await this._activateLegacy("manual", ++this.generation);
  }

  toggleSpeaker() { return (this.walnut || this.webRtc)?.toggleSpeaker(); }
  toggleMicrophone() { return (this.walnut || this.webRtc)?.toggleMicrophone(); }

  stop(notify = true) {
    if (this.stopping) return this.stopping;
    this.stopping = this._stop(notify).finally(() => { this.stopping = null; });
    return this.stopping;
  }

  async _stop(notify) {
    ++this.generation;
    const webRtc = this.webRtc; this.webRtc = null;
    const walnut = this.walnut; this.walnut = null;
    const legacy = this.legacy; this.legacy = null;
    this.mode = "idle";
    legacy?.stop();
    if (webRtc) await webRtc.stop(false);
    if (walnut) await walnut.stop(false);
    if (notify) this.onState({ phase: "idle", transport: null, microphone: false,
      speaker: false, legacyAvailable: false, message: copy(this, "Live terminato") });
  }

  _webRtcState(state, generation) {
    if (generation !== this.generation) return;
    if (state.phase === "fallback") {
      if (!this.fallbackUsed) {
        this.fallbackUsed = true;
        this._activateLegacy("automatic", generation).catch(() => {});
      }
      return;
    }
    if (state.phase === "error") this.mode = "error";
    this.onState({ ...state, transport: "webrtc",
      legacyAvailable: state.phase === "error" });
  }

  async _activateLegacy(trigger, generation) {
    this.mode = "switching";
    this.onState({ phase: "connecting", transport: "walnut", legacyAvailable: false,
      microphone: false, speaker: false, message: trigger === "automatic"
        ? copy(this, "Passaggio automatico al live compatibile…") : trigger === "policy"
          ? copy(this, "Apertura live Blink…") : copy(this, "Apertura live compatibile…") });
    const webRtc = this.webRtc; this.webRtc = null;
    const walnut = this.walnut; this.walnut = null;
    if (webRtc) await webRtc.stop(false);
    if (walnut) await walnut.stop(false);
    if (generation !== this.generation) return;
    const legacy = this.makeLegacy();
    this.legacy = legacy;
    try {
      await legacy.start(this.entityId);
      if (generation !== this.generation) { legacy.stop(); return; }
      this.mode = "legacy";
      this.onState({ phase: "active", transport: "walnut", legacyAvailable: false,
        microphone: false, speaker: false,
        message: copy(this, "Live Blink attivo · audio bidirezionale non disponibile per questo trasporto") });
    } catch (error) {
      legacy.stop(); this.legacy = null; this.mode = "error";
      this.onState({ phase: "error", transport: "walnut", legacyAvailable: false,
        message: error?.message || copy(this, "Live Blink compatibile non disponibile") });
    }
  }
}
