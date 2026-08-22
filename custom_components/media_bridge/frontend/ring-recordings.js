import { RingLocalRecorder } from "./ring-local-recorder.js?v=0.7.0";

class RingRecordings extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._active = false;
    this._requested = false;
    this._recording = false;
  }

  configure(hass, entry) {
    this._hass = hass;
    this._entry = entry;
    if (!this.shadowRoot.hasChildNodes()) this._mount();
    this._autoRecordEntity = entry.controls?.auto_record;
    this._recorder = new RingLocalRecorder(hass, entry, (state) => this._recorderState(state));
    this._renderAutoRecord();
    this._load();
  }

  set hass(value) {
    this._hass = value;
    if (this._recorder) this._recorder.hass = value;
    this._renderAutoRecord();
  }

  prepareCall() {
    this._active = false;
    this._requested = false;
    this._remoteStream = null;
    this._localStream = null;
    this._mode = "listen";
    this._renderButton();
    this.$("status").textContent = "Connessione in corso…";
  }

  setCallState(active) {
    const newlyActive = active && !this._active;
    this._active = active;
    if (newlyActive && this._autoRecordEnabled()) this._requested = true;
    if (active) this._maybeStart();
    this._renderButton();
  }

  setMedia(remoteStream, localStream, mode) {
    this._remoteStream = remoteStream;
    this._localStream = localStream;
    this._mode = mode;
    if (this._recorder?.active) this._recorder.updateLocal(localStream, mode === "talk");
    else this._maybeStart();
  }

  async finishCall() {
    this._active = false;
    this._requested = false;
    if (this._recorder?.active) await this._recorder.stop(true);
    this._renderButton();
  }

  _mount() {
    this.shadowRoot.innerHTML = `
      <style>
        :host{display:block;margin-top:16px}.card{padding:22px;border-radius:22px;
          background:var(--card-background-color);box-shadow:var(--ha-card-box-shadow);
          border:1px solid var(--divider-color)}.top{display:flex;justify-content:space-between;
          gap:16px;align-items:start}h2{margin:0 0 4px;font-size:19px}.hint{color:var(--secondary-text-color);
          font-size:14px;line-height:1.45}.badge{border-radius:999px;padding:7px 11px;font-weight:650;
          background:color-mix(in srgb,var(--primary-color) 15%,transparent)}button{width:100%;min-height:48px;
          margin-top:17px;border:0;border-radius:14px;padding:10px 14px;cursor:pointer;font:inherit;
          font-weight:700;color:white;background:linear-gradient(135deg,#b34377,#e36a49)}
        button:disabled{opacity:.48;cursor:not-allowed}.status{margin:13px 0 0;color:var(--secondary-text-color)}
        .toggle{display:flex;justify-content:space-between;align-items:center;gap:16px;margin-top:17px;
          padding:13px 0;border-top:1px solid var(--divider-color)}.toggle input{width:22px;height:22px;
          accent-color:var(--primary-color)}@media(max-width:520px){.card{padding:18px}}
      </style>
      <section class="card"><div class="top"><div><h2>Archivio chiamate</h2>
        <div class="hint" id="detail">Caricamento…</div></div><span class="badge" id="count">—</span></div>
        <label class="toggle"><span><strong>Registra automaticamente</strong><br>
          <span class="hint">Impostazione globale per le comunicazioni Vistoda</span></span>
          <input id="auto-record" type="checkbox" disabled></label>
        <button id="record" disabled>Registra questa chiamata</button>
        <p class="status" id="status">Avvia la comunicazione per registrare.</p>
        <p class="hint">La registrazione è locale nel bridge Vistoda e non richiede Call Recording
          di Ring. Include l’audio del citofono e il microfono quando lo attivi.</p>
      </section>`;
    this.$ = (id) => this.shadowRoot.getElementById(id);
    this.$("record").addEventListener("click", () => this._toggleRecording());
    this.$("auto-record").addEventListener("change", () => this._setAutoRecord());
  }

  _autoRecordEnabled() {
    return this._hass?.states?.[this._autoRecordEntity]?.state === "on";
  }

  _renderAutoRecord() {
    if (!this.$ || !this._hass) return;
    const state = this._hass.states?.[this._autoRecordEntity];
    const toggle = this.$("auto-record");
    toggle.disabled = !state || state.state === "unavailable";
    toggle.checked = state?.state === "on";
  }

  async _setAutoRecord() {
    const enabled = this.$("auto-record").checked;
    try {
      await this._hass.callService("switch", enabled ? "turn_on" : "turn_off", {
        entity_id: this._autoRecordEntity,
      });
      this.$("status").textContent = enabled
        ? "Registrazione automatica attiva per le prossime comunicazioni."
        : "Registrazione automatica disattivata.";
    } catch (_error) {
      this.$("status").textContent = "Impossibile aggiornare l’impostazione globale.";
      this._renderAutoRecord();
    }
  }

  async _toggleRecording() {
    if (this._recorder?.active) return this._recorder.stop(true);
    this._requested = true;
    await this._maybeStart();
  }

  async _maybeStart() {
    if (!this._requested || !this._active || !this._remoteStream || this._recorder?.active) return;
    try {
      await this._recorder.start(this._remoteStream, this._localStream, this._mode === "talk");
    } catch (error) {
      this._requested = false;
      this.$("status").textContent = error?.message || "Registrazione locale non disponibile.";
      this._renderButton();
    }
  }

  _recorderState(state) {
    const labels = {
      recording: "Registrazione locale in corso…",
      uploading: "Salvataggio nel bridge Vistoda…",
      saved: "Registrazione salvata nell’archivio privato.",
      upload_failed: "Salvataggio non riuscito; verifica il bridge Vistoda.",
      too_large: "Registrazione interrotta: limite archivio superato.",
      error: "Il browser ha interrotto la registrazione.",
    };
    this._recording = state === "recording";
    this.$("status").textContent = labels[state] || this.$("status").textContent;
    this._renderButton();
    if (state === "saved") this._load();
  }

  _renderButton() {
    if (!this.$) return;
    const button = this.$("record");
    button.disabled = !this._active && !this._recording;
    button.textContent = this._recording ? "Interrompi e salva" : "Registra questa chiamata";
  }

  async _load() {
    try {
      const result = await this._hass.callWS({
        type: "media_bridge/ring/recordings/list", entry_id: this._entry.entry_id,
      });
      const recordings = result.recordings || [];
      this.$("count").textContent = String(recordings.length);
      const latest = recordings[0];
      this.$("detail").textContent = latest
        ? `Ultima: ${new Date(latest.ended_at * 1000).toLocaleString("it-IT")}`
        : "Nessuna registrazione locale · conservazione 30 giorni";
    } catch (_error) {
      this.$("count").textContent = "!";
      this.$("detail").textContent = "Archivio temporaneamente non disponibile";
    }
  }

  disconnectedCallback() { this._recorder?.stop(true); }
}

customElements.define("vistoda-ring-recordings", RingRecordings);
