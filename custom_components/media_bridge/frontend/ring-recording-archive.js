import {
  recordingDate,
  recordingDuration,
  recordingPage,
  recordingSize,
} from "./recording-table.js";

class RingRecordingArchive extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._recordings = [];
    this._page = 1;
    this._busy = false;
  }

  configure(hass, entry) {
    this._hass = hass;
    this._entry = entry;
    if (!this.shadowRoot.hasChildNodes()) this._mount();
    this.load();
  }

  set hass(value) { this._hass = value; }

  _mount() {
    this.shadowRoot.innerHTML = `
      <style>
        :host{display:block;margin-top:18px;padding-top:17px;border-top:1px solid var(--divider-color)}
        *{box-sizing:border-box}.head{display:flex;justify-content:space-between;gap:14px;
          align-items:flex-start}h3{margin:0 0 4px;font-size:16px}.hint{color:var(--secondary-text-color);
          font-size:14px;line-height:1.45}.toolbar{display:flex;gap:7px;flex-wrap:wrap}button{min-height:38px;
          border:0;border-radius:11px;padding:7px 11px;cursor:pointer;font:inherit;font-weight:700;
          display:inline-flex;align-items:center;justify-content:center;gap:6px;color:var(--primary-text-color);
          background:var(--secondary-background-color)}button ha-icon{--mdc-icon-size:19px}
        button.danger{color:var(--error-color,#db4437)}button:disabled{opacity:.48;cursor:not-allowed}
        .table-wrap{overflow-x:auto;margin-top:12px}table{width:100%;border-collapse:collapse;min-width:560px}
        th,td{text-align:left;padding:10px 8px;border-bottom:1px solid var(--divider-color)}
        th{font-size:12px;color:var(--secondary-text-color);text-transform:uppercase;letter-spacing:.04em}
        td{font-size:14px}.row-action{min-height:34px;padding:5px 9px}.empty{text-align:center;padding:20px}
        .pager{display:flex;align-items:center;justify-content:flex-end;gap:9px;margin-top:12px}
        @media(max-width:520px){.head{display:block}.toolbar{margin-top:10px}.toolbar button{flex:1}
          .pager{justify-content:space-between}}
      </style>
      <div class="head"><div><h3>Registrazioni salvate</h3><div class="hint" id="status"
        role="status"></div></div><div class="toolbar"><button id="reload">
        <ha-icon icon="mdi:refresh"></ha-icon>Aggiorna</button><button class="danger" id="delete-all"
        disabled><ha-icon icon="mdi:delete-sweep-outline"></ha-icon>Elimina tutte</button></div></div>
      <div class="table-wrap" id="table-wrap"><table><thead><tr><th>Data</th><th>Durata</th>
        <th>Dimensione</th><th>Azioni</th></tr></thead><tbody id="rows"></tbody></table></div>
      <div class="empty hint" id="empty" hidden>Nessuna registrazione locale.</div>
      <nav class="pager" aria-label="Pagine archivio"><button id="previous"
        aria-label="Pagina precedente"><ha-icon icon="mdi:chevron-left"></ha-icon></button>
        <span id="page-label">Pagina 1 di 1</span><button id="next" aria-label="Pagina successiva">
        <ha-icon icon="mdi:chevron-right"></ha-icon></button></nav>`;
    this.$ = (id) => this.shadowRoot.getElementById(id);
    this.$("reload").addEventListener("click", () => this.load());
    this.$("delete-all").addEventListener("click", () => this._deleteAll());
    this.$("previous").addEventListener("click", () => this._changePage(-1));
    this.$("next").addEventListener("click", () => this._changePage(1));
  }

  async load() {
    this._setBusy(true, "Aggiornamento archivio…");
    try {
      const result = await this._hass.callWS({
        type: "media_bridge/ring/recordings/list",
        entry_id: this._entry.entry_id,
      });
      this._recordings = (result.recordings || []).sort((a, b) => b.ended_at - a.ended_at);
      this.dispatchEvent(new CustomEvent("archive-changed", {
        detail: { recordings: this._recordings },
      }));
      this.$("status").textContent = "";
    } catch (_error) {
      this.$("status").textContent = "Impossibile caricare le registrazioni.";
    } finally {
      this._setBusy(false);
      this._render();
    }
  }

  _render() {
    const page = recordingPage(this._recordings, this._page);
    this._page = page.page;
    this.$("rows").replaceChildren(...page.items.map((recording) => this._row(recording)));
    this.$("table-wrap").hidden = this._recordings.length === 0;
    this.$("empty").hidden = this._recordings.length !== 0;
    this.$("page-label").textContent = `Pagina ${page.page} di ${page.pages}`;
    this.$("previous").disabled = this._busy || page.page === 1;
    this.$("next").disabled = this._busy || page.page === page.pages;
    this.$("delete-all").disabled = this._busy || this._recordings.length === 0;
  }

  _row(recording) {
    const row = document.createElement("tr");
    for (const value of [this._date(recording), recordingDuration(recording), recordingSize(recording.bytes)]) {
      const cell = document.createElement("td");
      cell.textContent = value;
      row.append(cell);
    }
    const actions = document.createElement("td");
    const remove = document.createElement("button");
    remove.className = "danger row-action";
    remove.innerHTML = '<ha-icon icon="mdi:delete-outline"></ha-icon><span>Elimina</span>';
    remove.disabled = this._busy;
    remove.addEventListener("click", () => this._deleteOne(recording));
    actions.append(remove);
    row.append(actions);
    return row;
  }

  async _deleteOne(recording) {
    if (!window.confirm(`Eliminare la registrazione del ${this._date(recording)}?`)) return;
    await this._delete("media_bridge/ring/recordings/delete", {
      recording_id: recording.recording_id,
    }, "Registrazione eliminata.");
  }

  async _deleteAll() {
    const count = this._recordings.length;
    if (!window.confirm(`Eliminare definitivamente tutte le ${count} registrazioni?`)) return;
    await this._delete(
      "media_bridge/ring/recordings/delete_all", {}, `${count} registrazioni eliminate.`,
    );
  }

  async _delete(type, payload, success) {
    this._setBusy(true, "Eliminazione in corso…");
    try {
      const result = await this._hass.callWS({
        type, entry_id: this._entry.entry_id, ...payload,
      });
      await this.load();
      this.$("status").textContent = result.failed
        ? `${result.deleted} eliminate, ${result.failed} non eliminate.` : success;
    } catch (_error) {
      this.$("status").textContent = "Eliminazione non riuscita.";
    } finally {
      this._setBusy(false);
      this._render();
    }
  }

  _setBusy(busy, message = "") {
    this._busy = busy;
    if (this.$) {
      this.$("reload").disabled = busy;
      if (message) this.$("status").textContent = message;
    }
  }

  _changePage(step) { this._page += step; this._render(); }
  _date(recording) {
    return recordingDate(recording, this._hass?.locale?.language, this._hass?.config?.time_zone);
  }
}

if (!customElements.get("vistoda-ring-recording-archive")) {
  customElements.define("vistoda-ring-recording-archive", RingRecordingArchive);
}
