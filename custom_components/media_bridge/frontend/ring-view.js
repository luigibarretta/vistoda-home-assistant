import { copy, localizeCopy } from "./panel-copy.js";
import { RingAudioSession } from "./ring-audio-session.js";
import { saveRingEntry } from "./ring-entry-selection.js";
import { loadRingEntry } from "./ring-view-inventory.js";
import "./ring-controls.js";
import "./ring-recordings.js";
import "./ring-history.js";
import "./ring-device-identity.js";
import { BASE_STYLES } from "./panel-styles.js";
import { localizeElements } from "./panel-localize.js";
import { mountRingDeviceSelector, renderRingDeviceSelector, RING_DEVICE_SELECTOR_STYLES,
  RING_DEVICE_SELECTOR_TEMPLATE, setRingDeviceSelectorDisabled } from "./ring-device-selector.js";

class VistodaRingView extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._mounted = false;
    this._entry = null;
    this._audio = null;
    this._available = false;
    const query = new URLSearchParams(globalThis.location?.search || "");
    this._callId = query.get("answer") || "";
    this._requestedEntryId = query.get("entry") || "";
    this._storage = this._storageAccess();
    this._entries = [];
    this._answerMode = /^[A-Za-z0-9_-]{1,64}$/.test(this._callId);
    this._acknowledged = false;
    this._ackPending = false;
    this._ackAttempts = 0;
    this._entryGeneration = 0;
  }

  set hass(value) {
    this._hass = value;
    if (!this._mounted) this._mount();
    localizeCopy(this.shadowRoot, this); localizeElements(this.shadowRoot, value);
    if (this._entry) this.$("identity").configure(value, this._entry);
    if (this._audio) this._audio.hass = value;
    if (this.$?.("controls")) this.$("controls").hass = value;
    if (this.$?.("recordings")) this.$("recordings").hass = value;
  }

  async _mount() {
    this._mounted = true;
    this.shadowRoot.innerHTML = `
      <style>${BASE_STYLES}
        .call { padding:22px; }
        .device { display:flex; justify-content:space-between; gap:16px; align-items:start; }
        .device-copy { min-width:0;flex:1; }
        .status { display:flex; align-items:center; gap:9px; min-height:24px; margin:22px 0 14px; }
        .dot { width:10px; height:10px; border-radius:50%; background:var(--secondary-text-color); }
        .dot.live { background:var(--success-color,#43a047); box-shadow:0 0 0 5px #43a04725; }
        .actions button { min-height:40px; padding:8px 13px; display:inline-flex;
          align-items:center; justify-content:center; gap:7px; }
        .actions button[hidden] { display:none !important; }
        .actions ha-icon { --mdc-icon-size:20px; }
        .device-select { min-height:40px;max-width:100%;margin-top:11px;border:1px solid
          var(--divider-color);border-radius:11px;padding:7px 11px;color:var(--primary-text-color);
          background:var(--secondary-background-color);font:inherit; }
        ${RING_DEVICE_SELECTOR_STYLES}
        .spin { animation:spin 1s linear infinite; }
        @keyframes spin { to { transform:rotate(360deg); } }
        .privacy { margin:18px 0 0; padding-top:16px; border-top:1px solid var(--divider-color);
          color:var(--secondary-text-color); font-size:14px; line-height:1.5; }
        audio { width:100%; height:0; display:block; }
        @media (max-width:600px) { .call{padding:18px} .device{flex-wrap:wrap}
          .device-copy{flex-basis:100%} }
      </style>
      <section class="card empty" id="connection-state" hidden><p id="connection-message" role="status"></p>
        <button id="retry" data-i18n="retry">Riprova</button>
        <a class="button" href="/config/integrations/dashboard" data-i18n="reconnect">Gestisci collegamento</a></section>
      <div id="ring-main"><section class="card call">
        <div class="device"><div class="device-copy">
          <vistoda-ring-device-identity id="identity"></vistoda-ring-device-identity>
          ${RING_DEVICE_SELECTOR_TEMPLATE}</div>
          <span class="badge off" id="availability"><span data-copy="Verifica…">Verifica…</span></span></div>
        <div class="status"><span class="dot" id="dot"></span><span id="status"><span data-copy="Pronto">Pronto</span></span></div>
        <div class="actions"><button class="primary" id="call"><ha-icon id="call-icon"
          icon="mdi:phone"></ha-icon><span id="call-label"><span data-copy="Avvia comunicazione">Avvia comunicazione</span></span></button>
          <button id="microphone" hidden disabled><ha-icon id="microphone-icon"
            icon="mdi:microphone-off"></ha-icon><span id="microphone-label">
            <span data-copy="Attiva microfono">Attiva microfono</span></span></button><button id="history-open">
            <ha-icon icon="mdi:history"></ha-icon><span data-i18n="history">Cronologia eventi</span></button></div>
        <p class="privacy"><span data-copy="La sessione parte in solo ascolto. Il browser richiede il microfono soltanto quando lo attivi e lo rilascia tornando al solo ascolto. Dopo “Termina” un breve conto alla rovescia protegge Ring da chiamate ripetute.">La sessione parte in solo ascolto. Il browser richiede il microfono
          soltanto quando lo attivi e lo rilascia tornando al solo ascolto. Dopo “Termina” un
          breve conto alla rovescia protegge Ring da chiamate ripetute.</span></p>
        <audio id="remote" autoplay></audio>
      </section>
      <vistoda-ring-controls id="controls"></vistoda-ring-controls>
      <vistoda-ring-recordings id="recordings"></vistoda-ring-recordings></div>
      <vistoda-ring-history id="history" hidden></vistoda-ring-history>`; localizeCopy(this.shadowRoot, this);
    this.$ = (id) => this.shadowRoot.getElementById(id);
    localizeElements(this.shadowRoot, this._hass);
    this.$("retry").addEventListener("click", () => this._loadEntry());
    this.$("call").addEventListener("click", () => this._toggleCall());
    this.$("microphone").addEventListener("click", () => this._toggleMicrophone());
    this.$("identity").addEventListener("identity-updated", () => this._renderEntrySelector());
    this.$("history-open").addEventListener("click", () => this._showHistory(true));
    this.$("history").addEventListener("history-close", () => this._showHistory(false));
    mountRingDeviceSelector(this);
    await this._loadEntry();
  }

  _loadEntry() { return loadRingEntry(this); }

  _configureEntry() {
    this.$("identity").configure(this._hass, this._entry);
    this._audio = new RingAudioSession(
      this._hass, this._entry, this.$("remote"), (state) => this._renderState(state),
      (remote, local, mode) => this.$("recordings")?.setMedia(remote, local, mode),
      () => this.$("recordings")?.finishCall(),
    );
    this.$("controls").hass = this._hass;
    this.$("controls").configure(this._entry.controls, this._entry);
    this.$("recordings").configure(this._hass, this._entry);
  }

  async _selectEntry(entryId) {
    const entry = this._entries.find((item) => item.entry_id === entryId);
    if (!entry || entry === this._entry) return;
    const select = this.$("device-select");
    select.disabled = true;
    setRingDeviceSelectorDisabled(this, true);
    this._entryGeneration += 1;
    this._ackPending = false;
    if (entry.entry_id !== this._requestedEntryId) {
      this._answerMode = false;
      this._callId = "";
    }
    await this._audio?.destroy();
    this._entry = entry;
    this._available = Boolean(entry.available);
    saveRingEntry(this._storage, entry.entry_id);
    this._acknowledged = false;
    this._ackAttempts = 0;
    this._renderAvailability();
    this._configureEntry();
    this._renderEntrySelector();
    this._renderState({ phase: "idle" });
    select.disabled = false;
    setRingDeviceSelectorDisabled(this, false);
  }

  _renderEntrySelector() {
    renderRingDeviceSelector(this);
  }

  _renderAvailability() {
    const badge = this.$("availability");
    badge.textContent = this._available ? copy(this, "Disponibile") : copy(this, "Non disponibile");
    badge.classList.toggle("off", !this._available);
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
      idle: copy(this, "Pronto"), starting: talkMode ? copy(this, "Autorizza il microfono…") : copy(this, "Preparazione ascolto…"),
      connecting: copy(this, "Connessione a Ring…"), switching: talk
        ? copy(this, "Attivazione microfono…") : copy(this, "Ritorno al solo ascolto…"),
      active: talk ? copy(this, "Conversazione full-duplex attiva") : copy(this, "Ascolto attivo"),
    };
    const message = state.phase === "cooldown"
      ? copy(this, "Nuova sessione disponibile tra {p0} s", { p0: state.seconds }) : state.message || defaults[state.phase];
    this.$("status").textContent = message || copy(this, "Audio Ring non disponibile");
    this.$("dot").classList.toggle("live", active);
    const call = this.$("call");
    const connecting = ["starting", "connecting"].includes(state.phase);
    const startLabel = this._answerMode ? copy(this, "Rispondi in full-duplex") : copy(this, "Avvia comunicazione");
    const callLabel = ongoing ? copy(this, "Termina") : connecting ? copy(this, "Connessione…")
      : state.phase === "cooldown" ? copy(this, "Attendi {p0} s", { p0: state.seconds }) : startLabel;
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
    this.$("microphone-label").textContent = talk ? copy(this, "Disattiva microfono") : copy(this, "Attiva microfono");
    this.$("history-open").disabled = !this._entry || ongoing || locked;
    this.$("identity").setBusy(ongoing || locked);
    this.$("recordings")?.setCallState(ongoing);
  }

  _showHistory(open) {
    if ((open && this._audio?.pc) || !this._entry) return;
    this.$("ring-main").hidden = open;
    this.$("history").hidden = !open;
    if (open) this.$("history").configure(this._hass, this._entry);
    else this.$("history-open").focus();
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
    const entry = this._entry;
    const callId = this._callId;
    const generation = this._entryGeneration;
    this._ackPending = true;
    this._ackAttempts += 1;
    try {
      await this._hass.callWS({
        type: "media_bridge/ring/call/answer",
        entry_id: entry.entry_id,
        call_id: callId,
      });
      if (generation === this._entryGeneration && entry === this._entry && callId === this._callId) {
        this._acknowledged = true;
      }
    } catch (_error) {
      if (this._ackAttempts < 3) setTimeout(() => {
        if (generation === this._entryGeneration && entry === this._entry && callId === this._callId) {
          this._acknowledgeCall();
        }
      }, 1000);
    } finally {
      this._ackPending = false;
    }
  }

  _storageAccess() {
    try { return globalThis.localStorage; } catch (_error) { return null; }
  }

  disconnectedCallback() { this._audio?.destroy(); }
}

if (!customElements.get("vistoda-ring-view")) {
  customElements.define("vistoda-ring-view", VistodaRingView);
}
