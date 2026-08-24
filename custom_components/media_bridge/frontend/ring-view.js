import { RingAudioSession } from "./ring-audio-session.js";
import "./ring-controls.js";
import "./ring-recordings.js";
import { BASE_STYLES } from "./panel-styles.js";

class VistodaRingView extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._mounted = false;
    this._entry = null;
    this._audio = null;
    this._available = false;
    this._callId = new URLSearchParams(globalThis.location?.search || "").get("answer") || "";
    this._answerMode = /^[A-Za-z0-9_-]{1,64}$/.test(this._callId);
    this._acknowledged = false;
    this._ackPending = false;
    this._ackAttempts = 0;
  }

  set hass(value) {
    this._hass = value;
    if (!this._mounted) this._mount();
    if (this.$?.("controls")) this.$("controls").hass = value;
    if (this.$?.("recordings")) this.$("recordings").hass = value;
  }

  async _mount() {
    this._mounted = true;
    this.shadowRoot.innerHTML = `
      <style>${BASE_STYLES}
        .call { padding:22px; }
        .device { display:flex; justify-content:space-between; gap:16px; align-items:start; }
        h2 { margin:4px 0 7px; font-size:22px; }
        .status { display:flex; align-items:center; gap:9px; min-height:24px; margin:22px 0 14px; }
        .dot { width:10px; height:10px; border-radius:50%; background:var(--secondary-text-color); }
        .dot.live { background:var(--success-color,#43a047); box-shadow:0 0 0 5px #43a04725; }
        .actions button { min-height:40px; padding:8px 13px; display:inline-flex;
          align-items:center; justify-content:center; gap:7px; }
        .actions button[hidden] { display:none !important; }
        .actions ha-icon { --mdc-icon-size:20px; }
        .spin { animation:spin 1s linear infinite; }
        @keyframes spin { to { transform:rotate(360deg); } }
        .privacy { margin:18px 0 0; padding-top:16px; border-top:1px solid var(--divider-color);
          color:var(--secondary-text-color); font-size:14px; line-height:1.5; }
        audio { width:100%; height:0; display:block; }
        @media (max-width:600px) { .call{padding:18px} }
      </style>
      <section class="card call">
        <div class="device"><div><div class="eyebrow">Ring Intercom</div>
          <h2 id="device-name">Citofono</h2><div class="muted">Ascolto e conversazione
          simultanei · massimo 2 minuti</div></div>
          <span class="badge off" id="availability">Verifica…</span></div>
        <div class="status"><span class="dot" id="dot"></span><span id="status">Pronto</span></div>
        <div class="actions"><button class="primary" id="call"><ha-icon id="call-icon"
          icon="mdi:phone"></ha-icon><span id="call-label">Avvia comunicazione</span></button>
          <button id="microphone" hidden disabled><ha-icon id="microphone-icon"
            icon="mdi:microphone-off"></ha-icon><span id="microphone-label">
            Attiva microfono</span></button></div>
        <p class="privacy">La sessione parte in solo ascolto. Il browser richiede il microfono
          soltanto quando lo attivi e lo rilascia tornando al solo ascolto. Dopo “Termina” un
          breve conto alla rovescia protegge Ring da chiamate ripetute.</p>
        <audio id="remote" autoplay></audio>
      </section>
      <vistoda-ring-controls id="controls"></vistoda-ring-controls>
      <vistoda-ring-recordings id="recordings"></vistoda-ring-recordings>`;
    this.$ = (id) => this.shadowRoot.getElementById(id);
    this.$("call").addEventListener("click", () => this._toggleCall());
    this.$("microphone").addEventListener("click", () => this._toggleMicrophone());
    await this._loadEntry();
  }

  async _loadEntry() {
    try {
      const result = await this._hass.callWS({ type: "media_bridge/ring/info" });
      this._entry = result.entries[0] || null;
      this._available = Boolean(this._entry?.available);
      const badge = this.$("availability");
      badge.textContent = this._available ? "Disponibile" : "Non disponibile";
      badge.classList.toggle("off", !this._available);
      if (this._entry) this._configureEntry();
      this._renderState(this._entry ? { phase: "idle" } : {
        phase: "error", message: "Nessun bridge Ring configurato",
      });
    } catch (_error) {
      this._available = false;
      this._renderState({ phase: "error", message: "Impossibile leggere Vistoda · Ring" });
    }
  }

  _configureEntry() {
    this.$("device-name").textContent = this._entry.name.replace(/^Vistoda · /, "");
    this._audio = new RingAudioSession(
      this._hass, this._entry, this.$("remote"), (state) => this._renderState(state),
      (remote, local, mode) => this.$("recordings")?.setMedia(remote, local, mode),
      () => this.$("recordings")?.finishCall(),
    );
    this.$("controls").hass = this._hass;
    this.$("controls").configure(this._entry.controls);
    this.$("recordings").configure(this._hass, this._entry);
  }

  _renderState(state) {
    if (state.phase === "starting") this.$("recordings")?.prepareCall();
    const active = state.phase === "active";
    if (active && this._answerMode) this._acknowledgeCall();
    const ongoing = active || state.phase === "switching";
    const locked = ["starting", "connecting", "switching", "cooldown"].includes(state.phase);
    const talkMode = state.mode === "talk";
    const talk = active && talkMode;
    const defaults = {
      idle: "Pronto", starting: talkMode ? "Autorizza il microfono…" : "Preparazione ascolto…",
      connecting: "Connessione a Ring…", switching: talk
        ? "Attivazione microfono…" : "Ritorno al solo ascolto…",
      active: talk ? "Conversazione full-duplex attiva" : "Ascolto attivo",
    };
    const message = state.phase === "cooldown"
      ? `Nuova sessione disponibile tra ${state.seconds} s` : state.message || defaults[state.phase];
    this.$("status").textContent = message || "Audio Ring non disponibile";
    this.$("dot").classList.toggle("live", active);
    const call = this.$("call");
    const connecting = ["starting", "connecting"].includes(state.phase);
    const startLabel = this._answerMode ? "Rispondi in full-duplex" : "Avvia comunicazione";
    const callLabel = ongoing ? "Termina" : connecting ? "Connessione…"
      : state.phase === "cooldown" ? `Attendi ${state.seconds} s` : startLabel;
    const callIcon = ongoing ? "mdi:phone-hangup" : connecting ? "mdi:loading"
      : state.phase === "cooldown" ? "mdi:timer-sand" : "mdi:phone";
    call.disabled = !this._available || locked;
    call.classList.toggle("danger", ongoing);
    call.classList.toggle("primary", !ongoing);
    this.$("call-icon").setAttribute("icon", callIcon);
    this.$("call-icon").classList.toggle("spin", connecting);
    this.$("call-label").textContent = callLabel;
    this.$("microphone").hidden = !ongoing;
    this.$("microphone").disabled = !active || locked;
    this.$("microphone").classList.toggle("primary", talk);
    this.$("microphone-icon").setAttribute("icon", talk ? "mdi:microphone" : "mdi:microphone-off");
    this.$("microphone-label").textContent = talk ? "Disattiva microfono" : "Attiva microfono";
    this.$("recordings")?.setCallState(ongoing);
  }

  _toggleCall() {
    if (this._audio?.pc) this._audio.stop();
    else this._audio?.start(this._answerMode ? "talk" : "listen");
  }

  _toggleMicrophone() {
    this._audio?.switchMode(this._audio.mode === "talk" ? "listen" : "talk");
  }

  async _acknowledgeCall() {
    if (this._acknowledged || this._ackPending || !this._entry) return;
    this._ackPending = true;
    this._ackAttempts += 1;
    try {
      await this._hass.callWS({
        type: "media_bridge/ring/call/answer",
        entry_id: this._entry.entry_id,
        call_id: this._callId,
      });
      this._acknowledged = true;
    } catch (_error) {
      if (this._ackAttempts < 3) setTimeout(() => this._acknowledgeCall(), 1000);
    } finally {
      this._ackPending = false;
    }
  }

  disconnectedCallback() { this._audio?.destroy(); }
}

if (!customElements.get("vistoda-ring-view")) {
  customElements.define("vistoda-ring-view", VistodaRingView);
}
