import { copy } from "./panel-copy.js";
import { BlinkLiveSession } from "./blink-live-session.js";
import { LiveFullscreen } from "./live-fullscreen.js";
import { entityState, openMoreInfo, setText } from "./panel-helpers.js";

export const blinkViewLive = {
  async _toggleFullscreen() {
    if (this._liveControls?.mobile) return this._liveControls.close();
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
    if (this._liveSession?.active || this._liveOpening) return this._liveControls.close();
    if (this._liveSession && this._liveState.legacyAvailable) {
      return this._liveSession.startLegacy();
    }
    if (this._hass?.user?.is_admin !== true) {
      openMoreInfo(this, this._current("camera")); return;
    }
    const camera = entityState(this._hass, this._current("camera"));
    if (!camera?.attributes?.alias) return;
    this._liveControls.open();
    this._liveOpening = true;
    this._liveSnapshotWarning = "";
    this._liveState = { phase: "starting", message: copy(this, "Apertura live Blink…") };
    this._renderLive();
    let session;
    session = new BlinkLiveSession(
      this._hass, this.$("live-video"), this.$("legacy-live"), (state) => {
        if (this._liveSession !== session) return;
        this._liveState = { ...this._liveState, ...state };
        this._renderLive(); this._showImage(Boolean(this.$("snapshot").src));
      },
    );
    this._liveSession = session;
    // One explicit action, serialized provider commands: Blink may reject a
    // snapshot while live is already busy. Failure does not block viewing.
    const refreshed = await this._refreshSnapshot(true);
    if (this._liveSession !== session || !this._liveOpening) return;
    if (!refreshed) this._liveSnapshotWarning = copy(this,
      "Snapshot non aggiornato. Il video live è indipendente; riprova lo snapshot dopo averlo chiuso.");
    this._liveOpening = false;
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
    this._liveControls?.update(this._liveState);
    this.$("fullscreen").hidden = !connected && !this._liveControls?.mobile;
    this.$("rotate").hidden = !connected;
    if (this._liveControls?.mobile) {
      this.$("fullscreen").title = copy(this, "Chiudi live");
      this.$("fullscreen").setAttribute("aria-label", copy(this, "Chiudi live"));
      this.$("fullscreen").querySelector("ha-icon").setAttribute("icon", "mdi:close");
    }
    this._fullscreen?.update();
    if (!active) { this._fullscreen?.exit().catch(() => {}); this._liveControls?.reset(); }
    this.$("live").classList.toggle("danger", active);
    this.$("live").querySelector("ha-icon").setAttribute("icon", active
      ? "mdi:video-off-outline" : "mdi:video-wireless-outline");
    this.$("live").querySelector("span").textContent = active ? copy(this, "Chiudi live") :
      this._liveState.legacyAvailable ? copy(this, "Apri live compatibile") : copy(this, "Apri live");
    this.$("live").title = this.$("live").querySelector("span").textContent;
    this.$("speaker").hidden = !connected; this.$("microphone").hidden = !connected;
    this.$("microphone-unavailable").hidden = !connected || interactive;
    this.$("speaker").disabled = !connected;
    this.$("microphone").disabled = !interactive;
    this.$("refresh").hidden = active; this.$("motion").hidden = active;
    this.$("speaker").classList.toggle("primary", Boolean(this._liveState.speaker));
    this.$("microphone").classList.toggle("primary", Boolean(this._liveState.microphone));
    this.$("speaker").setAttribute("aria-pressed", String(Boolean(this._liveState.speaker)));
    this.$("microphone").setAttribute("aria-pressed", String(Boolean(this._liveState.microphone)));
    this.$("microphone").setAttribute("aria-busy", String(Boolean(this._liveState.microphonePending)));
    this.$("talk-status").hidden = !interactive;
    setText(this.shadowRoot, "talk-status", copy(this, this._liveState.microphone
      ? "Microfono attivo" : "Tieni premuto per parlare"));
    this.$("microphone").setAttribute("aria-describedby", "live-message");
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
      ? copy(this, "Microfono attivo") : copy(this, "Tieni premuto per parlare"));
    this.$("speaker").title = this.$("speaker-label").textContent;
    this.$("microphone").title = copy(this, "Tieni premuto per parlare");
    this.$("live-message").hidden = !active;
    setText(this.shadowRoot, "live-message", [this._liveState.message,
      this._liveSnapshotWarning].filter(Boolean).join(" · "));
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
    this._liveControls?.dispose();
    this._fullscreen?.dispose(); this._fullscreen = null;
    this._liveSession?.stop(false);
  },
};
