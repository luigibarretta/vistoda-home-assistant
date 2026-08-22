const TERMINAL = new Set(["complete", "unavailable", "expired", "failed"]);

class RingRecordings extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._callStartedAt = null;
    this._timer = null;
  }

  configure(hass, entry) {
    this._hass = hass;
    this._entry = entry;
    if (!this.shadowRoot.hasChildNodes()) this._mount();
    this._load();
  }

  setCallState(active) {
    if (active && !this._callStartedAt) this._callStartedAt = Math.floor(Date.now() / 1000);
    this.$("record").disabled = !active || Boolean(this._importId);
  }

  prepareCall() {
    if (this._importId && !this._terminal) return;
    this._callStartedAt = null;
    this._importId = null;
    this._terminal = false;
    this.$("status").textContent = "Connessione in corso; attendi che la chiamata sia attiva.";
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
        @media(max-width:520px){.card{padding:18px}}
      </style>
      <section class="card"><div class="top"><div><h2>Archivio chiamate</h2>
        <div class="hint" id="detail">Caricamento…</div></div><span class="badge" id="count">—</span></div>
        <button id="record" disabled>Registra questa chiamata</button>
        <p class="status" id="status">Avvia la comunicazione per abilitare la registrazione.</p>
        <p class="hint">Usa la registrazione ufficiale Ring: l’avviso vocale resta attivo e
          “Call Recording” deve essere abilitato nelle impostazioni Privacy dell’app Ring.</p>
      </section>`;
    this.$ = (id) => this.shadowRoot.getElementById(id);
    this.$("record").addEventListener("click", () => this._start());
  }

  async _start() {
    if (!this._callStartedAt || this._importId) return;
    this.$("record").disabled = true;
    this.$("status").textContent = "Richiesta di registrazione in corso…";
    try {
      const result = await this._hass.callWS({
        type: "media_bridge/ring/recordings/import",
        entry_id: this._entry.entry_id,
        triggered_at: this._callStartedAt,
      });
      this._importId = result.import_id;
      this._pollCount = 0;
      this._terminal = TERMINAL.has(result.state);
      this._renderImport(result.state);
      if (!TERMINAL.has(result.state)) this._schedulePoll();
    } catch (_error) {
      this.$("status").textContent = "Richiesta rifiutata: verifica bridge e impostazioni Ring.";
      this.$("record").disabled = false;
    }
  }

  _schedulePoll() {
    clearTimeout(this._timer);
    this._timer = setTimeout(() => this._poll(), 5000);
  }

  async _poll() {
    this._pollCount += 1;
    if (this._pollCount > 45) {
      this.$("status").textContent = "Tempo di attesa scaduto; verifica più tardi l’archivio.";
      return;
    }
    try {
      const result = await this._hass.callWS({
        type: "media_bridge/ring/recordings/import/status",
        entry_id: this._entry.entry_id,
        import_id: this._importId,
      });
      this._terminal = TERMINAL.has(result.state);
      this._renderImport(result.state);
      if (TERMINAL.has(result.state)) {
        if (result.state === "complete") await this._load();
      } else this._schedulePoll();
    } catch (_error) {
      this.$("status").textContent = "Stato non raggiungibile; il bridge continua in background.";
      this._schedulePoll();
    }
  }

  _renderImport(state) {
    const labels = {
      pending: "Ring sta finalizzando la registrazione…",
      complete: "Registrazione completata e archiviata.",
      unavailable: "Call Recording non è abilitato o disponibile per questo account.",
      expired: "Nessuna registrazione completata trovata per questa chiamata.",
      failed: "Import non riuscito; consulta i log del bridge.",
    };
    this.$("status").textContent = labels[state] || "Stato registrazione sconosciuto.";
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
        ? `Ultima: ${new Date(latest.event_at * 1000).toLocaleString("it-IT")}`
        : "Nessuna registrazione importata · conservazione 30 giorni";
    } catch (_error) {
      this.$("count").textContent = "!";
      this.$("detail").textContent = "Archivio temporaneamente non disponibile";
    }
  }

  disconnectedCallback() { clearTimeout(this._timer); }
}

customElements.define("vistoda-ring-recordings", RingRecordings);
