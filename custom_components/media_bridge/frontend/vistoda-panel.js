import { RingAudioSession } from "./ring-audio-session.js?v=0.7.1";
import "./ring-controls.js?v=0.7.1";
import "./ring-recordings.js?v=0.7.1";

class VistodaPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._mounted = false;
    this._entry = null;
    this._audio = null;
    this._available = false;
    this._answerMode = new URLSearchParams(globalThis.location?.search || "").get("answer") === "1";
  }

  set hass(value) {
    this._hass = value;
    if (!this._mounted) this._mount();
    if (this.$?.("controls")) this.$("controls").hass = value;
    if (this.$?.("recordings")) this.$("recordings").hass = value;
  }

  set panel(value) { this._panel = value; }

  async _mount() {
    this._mounted = true;
    this.shadowRoot.innerHTML = `
      <style>
        :host { display:block; min-height:100%; color:var(--primary-text-color); }
        main { box-sizing:border-box; max-width:820px; margin:0 auto; padding:28px 18px 48px; }
        header { display:flex; align-items:center; gap:15px; margin-bottom:22px; }
        .mark { display:grid; place-items:center; width:54px; height:54px; border-radius:18px;
          background:linear-gradient(145deg,#6246ea,#27b3a2); color:white; font-size:27px; }
        h1 { font-size:27px; margin:0; } header p { margin:3px 0 0; color:var(--secondary-text-color); }
        .card { padding:22px; border-radius:22px; background:var(--card-background-color);
          box-shadow:var(--ha-card-box-shadow); border:1px solid var(--divider-color); }
        .provider { color:var(--primary-color); font-size:12px; font-weight:750; letter-spacing:.08em; }
        .device { display:flex; justify-content:space-between; gap:16px; align-items:start; }
        h2 { margin:4px 0 7px; font-size:21px; } .hint { color:var(--secondary-text-color); line-height:1.45; }
        .badge { border-radius:999px; padding:7px 11px; font-weight:650; white-space:nowrap;
          background:color-mix(in srgb,var(--success-color,#43a047) 18%,transparent); }
        .badge.off { background:color-mix(in srgb,var(--error-color,#db4437) 16%,transparent); }
        .status { display:flex; align-items:center; gap:9px; min-height:24px; margin:22px 0 14px; }
        .dot { width:10px; height:10px; border-radius:50%; background:var(--secondary-text-color); }
        .dot.live { background:var(--success-color,#43a047); box-shadow:0 0 0 5px #43a04725; }
        .actions { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px; }
        button { min-height:50px; border:0; border-radius:14px; padding:10px 14px; cursor:pointer;
          font:inherit; font-weight:650; color:var(--primary-text-color); background:var(--secondary-background-color); }
        button.primary { color:white; background:linear-gradient(135deg,#6246ea,#4967e9); }
        button.talk { color:white; background:linear-gradient(135deg,#d84d75,#f47740); }
        button:disabled { opacity:.48; cursor:not-allowed; }
        .privacy { margin:18px 0 0; padding-top:16px; border-top:1px solid var(--divider-color);
          color:var(--secondary-text-color); font-size:14px; line-height:1.5; }
        audio { width:100%; height:0; display:block; }
        @media (max-width:520px) { main{padding:18px 12px 36px}.card{padding:18px}.actions{grid-template-columns:1fr} }
      </style>
      <main>
        <header>
          <div class="mark">◉</div>
          <div><h1>Vistoda · Ring</h1><p>Audio privato del citofono Ring Intercom</p></div>
        </header>
        <section class="card">
          <div class="device">
            <div><div class="provider">RING INTERCOM</div><h2 id="device-name">Citofono</h2>
              <div class="hint">Ascolto e conversazione simultanei · massimo 2 minuti</div></div>
            <span class="badge off" id="availability">Verifica…</span>
          </div>
          <div class="status"><span class="dot" id="dot"></span><span id="status">Pronto</span></div>
          <div class="actions">
            <button class="primary" id="start">Avvia comunicazione</button>
            <button class="talk" id="microphone" disabled>Attiva microfono</button>
            <button id="stop" disabled>Termina</button>
          </div>
          <p class="privacy">La sessione parte in solo ascolto. Il browser richiede il microfono soltanto
            quando lo attivi e lo rilascia quando torni al solo ascolto. Dopo “Termina” un breve conto alla
            rovescia protegge Ring da chiamate ripetute.</p>
          <audio id="remote" autoplay></audio>
        </section>
        <vistoda-ring-controls id="controls"></vistoda-ring-controls>
        <vistoda-ring-recordings id="recordings"></vistoda-ring-recordings>
      </main>`;
    this.$ = (id) => this.shadowRoot.getElementById(id);
    this.$("start").addEventListener("click", () => this._audio?.start(this._answerMode ? "talk" : "listen"));
    this.$("microphone").addEventListener("click", () => this._toggleMicrophone());
    this.$("stop").addEventListener("click", () => this._audio?.stop());
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
      if (this._entry) {
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
      this._renderState(this._entry ? { phase: "idle" } : {
        phase: "error", message: "Nessun bridge Ring configurato",
      });
    } catch (_error) {
      this._available = false;
      this._renderState({ phase: "error", message: "Impossibile leggere Vistoda · Ring" });
    }
  }

  _renderState(state) {
    if (state.phase === "starting") this.$("recordings")?.prepareCall();
    const active = state.phase === "active";
    const callOngoing = active || state.phase === "switching";
    const locked = ["starting", "connecting", "switching", "cooldown"].includes(state.phase);
    const talk = active && state.mode === "talk";
    let message = state.message;
    if (!message && state.phase === "idle") message = "Pronto";
    if (!message && state.phase === "starting") message = state.mode === "talk"
      ? "Autorizza il microfono…" : "Preparazione ascolto…";
    if (!message && state.phase === "connecting") message = "Connessione a Ring…";
    if (!message && state.phase === "switching") message = state.mode === "talk"
      ? "Attivazione microfono…" : "Ritorno al solo ascolto…";
    if (!message && state.phase === "active") message = talk
      ? "Conversazione full-duplex attiva" : "Ascolto attivo";
    if (state.phase === "cooldown") message = `Nuova sessione disponibile tra ${state.seconds} s`;
    this._status(message || "Audio Ring non disponibile", active);
    this.$("start").disabled = !this._available || locked || active;
    this.$("microphone").disabled = !active || locked;
    this.$("stop").disabled = !active;
    this.$("start").textContent = active ? "Comunicazione attiva"
      : this._answerMode ? "Rispondi in full-duplex" : "Avvia comunicazione";
    this.$("microphone").textContent = talk ? "Disattiva microfono" : "Attiva microfono";
    this.$("recordings")?.setCallState(callOngoing);
  }

  _toggleMicrophone() {
    if (!this._audio) return;
    this._audio.switchMode(this._audio.mode === "talk" ? "listen" : "talk");
  }

  _status(text, live = false) {
    this.$("status").textContent = text;
    this.$("dot").classList.toggle("live", live);
  }

  disconnectedCallback() { this._audio?.destroy(); }
}

if (!customElements.get("vistoda-panel")) {
  customElements.define("vistoda-panel", VistodaPanel);
}
