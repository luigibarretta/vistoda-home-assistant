import { copy } from "./panel-copy.js";
import { BlinkLiveSession } from "./blink-live-session.js";
import { LiveFullscreen } from "./live-fullscreen.js";
import { entityState, openMoreInfo, setText } from "./panel-helpers.js";

export const blinkViewLive = {
  async _toggleFullscreen() {
    this._fullscreen ||= new LiveFullscreen(this.$("stage"), (active) => {
      const label = copy(this, active ? "Esci da schermo intero" : "Schermo intero");
      const button = this.$("fullscreen");
      button.title = label; button.setAttribute("aria-label", label);
      button.setAttribute("aria-pressed", String(active));
      button.querySelector("ha-icon").setAttribute("icon", active
        ? "mdi:fullscreen-exit" : "mdi:fullscreen");
    });
    try { await this._fullscreen.toggle(); }
    catch { setText(this.shadowRoot, "message", copy(this, "Schermo intero non disponibile in questo browser")); }
  },

  async _toggleLive() {
    if (this._liveSession?.active) return this._liveSession.stop();
    if (this._liveSession && this._liveState.legacyAvailable) {
      return this._liveSession.startLegacy();
    }
    if (this._hass?.user?.is_admin !== true) {
      openMoreInfo(this, this._current("camera")); return;
    }
    const camera = entityState(this._hass, this._current("camera"));
    if (!camera?.attributes?.alias) return;
    let session;
    session = new BlinkLiveSession(
      this._hass, this.$("live-video"), this.$("legacy-live"), (state) => {
        if (this._liveSession !== session) return;
        this._liveState = { ...this._liveState, ...state };
        this._renderLive(); this._showImage(Boolean(this.$("snapshot").src));
      },
    );
    this._liveSession = session;
    const preferredTransport = camera.attributes.preferred_live_transport === "cayuga"
      ? "cayuga" : "walnut";
    await this._liveSession.start(
      camera.attributes.alias, this._current("camera").entity_id, preferredTransport,
    );
  },

  _renderLive() {
    const active = ["starting", "connecting", "active"].includes(this._liveState.phase);
    const connected = this._liveState.phase === "active";
    const interactive = connected && (this._liveState.transport === "webrtc" ||
      this._liveState.microphoneSupported === true);
    this.$("fullscreen").hidden = !connected;
    this._fullscreen?.update();
    if (!active) this._fullscreen?.exit().catch(() => {});
    this.$("live").classList.toggle("danger", active);
    this.$("live").querySelector("ha-icon").setAttribute("icon", active
      ? "mdi:video-off-outline" : "mdi:video-wireless-outline");
    this.$("live").querySelector("span").textContent = active ? copy(this, "Chiudi live") :
      this._liveState.legacyAvailable ? copy(this, "Apri live compatibile") : copy(this, "Apri live");
    this.$("speaker").hidden = !interactive; this.$("microphone").hidden = !connected;
    this.$("microphone-unavailable").hidden = !connected || interactive;
    this.$("speaker").disabled = !interactive;
    this.$("microphone").disabled = !interactive || Boolean(this._liveState.microphonePending);
    this.$("speaker").classList.toggle("primary", Boolean(this._liveState.speaker));
    this.$("microphone").classList.toggle("primary", Boolean(this._liveState.microphone));
    this.$("speaker").setAttribute("aria-pressed", String(Boolean(this._liveState.speaker)));
    this.$("microphone").setAttribute("aria-pressed", String(Boolean(this._liveState.microphone)));
    this.$("microphone").setAttribute("aria-busy", String(Boolean(this._liveState.microphonePending)));
    this.$("microphone").setAttribute("aria-describedby", interactive ? "message" : "microphone-unavailable");
    this.$("microphone").title = copy(this, this._liveState.transport === "walnut"
      ? this._liveState.microphone ? "Disattiva il microfono per riprendere l’ascolto"
        : "Parla alla telecamera: l’ascolto viene sospeso mentre il microfono è attivo"
      : this._liveState.microphone ? "Disattiva microfono" : "Attiva microfono");
    this.$("speaker-icon").setAttribute("icon", this._liveState.speaker
      ? "mdi:volume-high" : "mdi:volume-off");
    this.$("microphone-icon").setAttribute("icon", this._liveState.microphone
      ? "mdi:microphone" : "mdi:microphone-off");
    setText(this.shadowRoot, "speaker-label", this._liveState.speaker
      ? copy(this, "Disattiva audio") : copy(this, "Attiva audio"));
    setText(this.shadowRoot, "microphone-label", this._liveState.microphone
      ? copy(this, "Disattiva microfono") : copy(this, "Attiva microfono"));
    if (this._liveState.message) setText(this.shadowRoot, "message", this._liveState.message);
  },

  _showImage(show) {
    const live = ["starting", "connecting", "active"].includes(this._liveState.phase);
    const legacy = live && this._liveState.transport === "walnut";
    this.$("live-video").hidden = !live || legacy;
    this.$("legacy-live").hidden = !legacy;
    this.$("snapshot").hidden = live || !show;
    this.$("placeholder").hidden = live || show;
  },

  disconnectedCallback() {
    this._fullscreen?.dispose(); this._fullscreen = null;
    this._liveSession?.stop(false);
  },
};
