import { copy, localizeCopy } from "./panel-copy.js";
import { RingLocalRecorder } from "./ring-local-recorder.js";
import "./ring-recording-archive.js";
import { BASE_STYLES } from "./panel-styles.js";

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
    this.$("archive").configure(hass, entry);
    this._renderAutoRecord();
  }

  set hass(value) {
    this._hass = value;
    if (this._recorder) this._recorder.hass = value;
    if (this.$?.("archive")) this.$("archive").hass = value;
    this._renderAutoRecord();
  }

  prepareCall() {
    this._active = false;
    this._requested = false;
    this._remoteStream = null;
    this._localStream = null;
    this._mode = "listen";
    this._renderButton();
    this.$("status").textContent = copy(this, "Connessione in corso…");
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
      <style>${BASE_STYLES}
        :host{display:block;margin-top:16px}.card{padding:20px;border-radius:22px;
          background:var(--card-background-color);box-shadow:var(--ha-card-box-shadow);
          border:1px solid var(--divider-color)}.top{display:flex;justify-content:space-between;
          gap:14px;align-items:flex-start}h2{margin:0 0 4px;font-size:19px}.hint,.status{
          color:var(--secondary-text-color);font-size:14px;line-height:1.45}.badge{border-radius:999px;
          padding:7px 11px;font-weight:650;background:color-mix(in srgb,var(--primary-color) 15%,transparent)}
        button{min-height:40px;border:0;border-radius:11px;padding:8px 12px;cursor:pointer;font:inherit;
          font-weight:700;display:inline-flex;align-items:center;gap:7px;color:white;
          background:linear-gradient(135deg,#b34377,#e36a49)}button ha-icon{--mdc-icon-size:20px}
        button[data-tooltip]{position:relative}button[data-tooltip]::after{content:attr(data-tooltip);
          position:absolute;z-index:20;top:calc(100% + 8px);left:0;width:max-content;
          max-width:min(280px,75vw);padding:8px 10px;border-radius:9px;color:var(--primary-text-color);
          background:var(--card-background-color);border:1px solid var(--divider-color);
          box-shadow:var(--ha-card-box-shadow);font-size:12px;line-height:1.35;text-align:left;
          white-space:normal;opacity:0;visibility:hidden;pointer-events:none}
        button[data-tooltip]:hover::after,button[data-tooltip]:focus-visible::after{opacity:1;visibility:visible}
        button:disabled{opacity:.48;cursor:not-allowed}.status{margin:10px 0}.toggle{display:flex;
          justify-content:space-between;align-items:center;gap:16px;margin-top:15px;padding:13px 0;
          border-top:1px solid var(--divider-color)}.toggle input{width:22px;height:22px;
          accent-color:var(--primary-color)}@media(max-width:520px){.card{padding:17px}}
      </style>
      <section class="card"><div class="top"><div><h2><span data-copy="Archivio chiamate">Archivio chiamate</span></h2>
        <div class="hint" id="detail"><span data-copy="Caricamento…">Caricamento…</span></div></div><span class="badge" id="count">—</span></div>
        <label class="toggle"><span><strong><span data-copy="Registra automaticamente">Registra automaticamente</span></strong><br>
          <span class="hint"><span data-copy="Impostazione globale per le comunicazioni Vistoda">Impostazione globale per le comunicazioni Vistoda</span></span></span>
          <input id="auto-record" type="checkbox" disabled></label>
        <button id="record" disabled aria-label="Registra questa chiamata" data-copy-aria-label="Registra questa chiamata"
          title="Avvia una registrazione locale della chiamata" data-copy-title="Avvia una registrazione locale della chiamata"><ha-icon id="record-icon"
          icon="mdi:record"></ha-icon>
          <span id="record-label"><span data-copy="Registra questa chiamata">Registra questa chiamata</span></span></button>
        <p class="status" id="status"><span data-copy="Avvia la comunicazione per registrare.">Avvia la comunicazione per registrare.</span></p>
        <p class="hint"><span data-copy="La registrazione è locale nel bridge Vistoda e non richiede Call Recording di Ring. Include l’audio del citofono e il microfono quando lo attivi.">La registrazione è locale nel bridge Vistoda e non richiede Call Recording
          di Ring. Include l’audio del citofono e il microfono quando lo attivi.</span></p>
        <vistoda-ring-recording-archive id="archive"></vistoda-ring-recording-archive>
      </section>`; localizeCopy(this.shadowRoot, this);
    this.$ = (id) => this.shadowRoot.getElementById(id);
    this.$("record").addEventListener("click", () => this._toggleRecording());
    this.$("auto-record").addEventListener("change", () => this._setAutoRecord());
    this.$("archive").addEventListener("archive-changed", (event) => {
      const recordings = event.detail.recordings;
      this.$("count").textContent = String(recordings.length);
      this.$("detail").textContent = recordings.length
        ? copy(this, "Registrazioni locali ordinate dalla più recente") : copy(this, "Nessuna registrazione locale · 30 giorni");
    });
  }

  _autoRecordEnabled() { return this._hass?.states?.[this._autoRecordEntity]?.state === "on"; }

  _renderAutoRecord() {
    if (!this.$ || !this._hass) return;
    localizeCopy(this.shadowRoot, this);
    const state = this._hass.states?.[this._autoRecordEntity];
    this.$("auto-record").disabled = !state || state.state === "unavailable";
    this.$("auto-record").checked = state?.state === "on";
  }

  async _setAutoRecord() {
    const enabled = this.$("auto-record").checked;
    try {
      await this._hass.callService("switch", enabled ? "turn_on" : "turn_off", {
        entity_id: this._autoRecordEntity,
      });
      this.$("status").textContent = enabled ? copy(this, "Registrazione automatica attiva.")
        : copy(this, "Registrazione automatica disattivata.");
    } catch (_error) {
      this.$("status").textContent = copy(this, "Impossibile aggiornare l’impostazione globale.");
      this._renderAutoRecord();
    }
  }

  async _toggleRecording() {
    if (this._recorder?.paused) return this._recorder.resume();
    if (this._recorder?.active) return this._recorder.pause();
    this._requested = true;
    await this._maybeStart();
  }

  async _maybeStart() {
    if (!this._requested || !this._active || !this._remoteStream || this._recorder?.active) return;
    try { await this._recorder.start(this._remoteStream, this._localStream, this._mode === "talk"); }
    catch (error) {
      this._requested = false;
      this.$("status").textContent = error?.message || copy(this, "Registrazione locale non disponibile.");
      this._renderButton();
    }
  }

  _recorderState(state) {
    const labels = { recording:copy(this, "Registrazione locale in corso…"), paused:copy(this, "Registrazione in pausa; la chiamata continua."), uploading:copy(this, "Salvataggio…"),
      saved:copy(this, "Registrazione salvata."), upload_failed:copy(this, "Salvataggio non riuscito."),
      too_large:copy(this, "Registrazione interrotta: limite superato."), error:copy(this, "Registrazione interrotta.") };
    this._recording = ["recording", "paused"].includes(state);
    this.$("status").textContent = labels[state] || this.$("status").textContent;
    this._renderButton();
    if (state === "saved") this.$("archive").load();
  }

  _renderButton() {
    if (!this.$) return;
    const paused = this._recorder?.paused;
    this.$("record").disabled = !this._active && !this._recording;
    const label = paused ? copy(this, "Riprendi registrazione")
      : this._recording ? copy(this, "Pausa registrazione") : copy(this, "Registra questa chiamata");
    const help = paused
      ? copy(this, "Riprende la registrazione; la comunicazione è rimasta attiva")
      : this._recording
        ? copy(this, "Mette in pausa soltanto la registrazione; la comunicazione resta attiva e il file sarà salvato al termine")
        : copy(this, "Avvia una registrazione locale della chiamata");
    this.$("record-label").textContent = label;
    this.$("record-icon").setAttribute("icon", paused ? "mdi:record-rec" : this._recording
      ? "mdi:pause" : "mdi:record");
    this.$("record").setAttribute("aria-label", label);
    this.$("record").title = help;
    this.$("record").dataset.tooltip = help;
  }

  disconnectedCallback() { this._recorder?.stop(true); }
}

if (!customElements.get("vistoda-ring-recordings")) {
  customElements.define("vistoda-ring-recordings", RingRecordings);
}
