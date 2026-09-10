import { BlinkWebRtcSession } from "./blink-webrtc-session.js";
import { entityState, openMoreInfo, setText } from "./panel-helpers.js";

export const blinkViewLive = {
  async _toggleLive() {
    if (this._liveSession?.pc) return this._liveSession.stop();
    if (this._hass?.user?.is_admin !== true) {
      openMoreInfo(this, this._current("camera")); return;
    }
    const camera = entityState(this._hass, this._current("camera"));
    if (!camera?.attributes?.alias) return;
    let session;
    session = new BlinkWebRtcSession(
      this._hass, this.$("live-video"), (state) => {
        if (this._liveSession !== session) return;
        this._liveState = { ...this._liveState, ...state };
        this._renderLive(); this._showImage(Boolean(this.$("snapshot").src));
      },
    );
    this._liveSession = session;
    await this._liveSession.start(camera.attributes.alias);
  },

  _renderLive() {
    const active = ["starting", "connecting", "active"].includes(this._liveState.phase);
    const connected = this._liveState.phase === "active";
    this.$("live").classList.toggle("danger", active);
    this.$("live").querySelector("ha-icon").setAttribute("icon", active
      ? "mdi:video-off-outline" : "mdi:video-wireless-outline");
    this.$("live").querySelector("span").textContent = active ? "Chiudi live" : "Apri live";
    this.$("speaker").hidden = !active; this.$("microphone").hidden = !active;
    this.$("speaker").disabled = !connected;
    this.$("microphone").disabled = !connected || Boolean(this._liveState.microphonePending);
    this.$("speaker").classList.toggle("primary", Boolean(this._liveState.speaker));
    this.$("microphone").classList.toggle("primary", Boolean(this._liveState.microphone));
    this.$("speaker").setAttribute("aria-pressed", String(Boolean(this._liveState.speaker)));
    this.$("microphone").setAttribute("aria-pressed", String(Boolean(this._liveState.microphone)));
    this.$("microphone").setAttribute("aria-busy", String(Boolean(this._liveState.microphonePending)));
    this.$("speaker-icon").setAttribute("icon", this._liveState.speaker
      ? "mdi:volume-high" : "mdi:volume-off");
    this.$("microphone-icon").setAttribute("icon", this._liveState.microphone
      ? "mdi:microphone" : "mdi:microphone-off");
    setText(this.shadowRoot, "speaker-label", this._liveState.speaker
      ? "Disattiva audio" : "Attiva audio");
    setText(this.shadowRoot, "microphone-label", this._liveState.microphone
      ? "Disattiva microfono" : "Attiva microfono");
    if (this._liveState.message) setText(this.shadowRoot, "message", this._liveState.message);
  },

  _showImage(show) {
    const live = ["starting", "connecting", "active"].includes(this._liveState.phase);
    this.$("live-video").hidden = !live;
    this.$("snapshot").hidden = live || !show;
    this.$("placeholder").hidden = live || show;
  },

  disconnectedCallback() { this._liveSession?.stop(false); },
};
