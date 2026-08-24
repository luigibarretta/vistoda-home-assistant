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
    this._activeId = null;
    this._loadingId = null;
    this._mediaUrl = null;
    this._player = null;
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
        td{font-size:14px}.row-actions,.player{display:flex;align-items:center;gap:7px}
        .row-action{min-height:34px;padding:5px 9px}.player-row td{padding:12px 8px;background:var(--secondary-background-color)}
        .player{flex-wrap:wrap}.player audio{min-width:220px;flex:1;height:40px}.empty{text-align:center;padding:20px}
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
      if (this._activeId && !this._recordings.some((item) => item.recording_id === this._activeId)) this._releaseMedia();
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
    this._player = null;
    const rows = page.items.flatMap((recording) => {
      const result = [this._row(recording)];
      if ([this._activeId, this._loadingId].includes(recording.recording_id)) {
        result.push(this._playerRow(recording));
      }
      return result;
    });
    this.$("rows").replaceChildren(...rows);
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
    actions.className = "row-actions";
    const play = document.createElement("button");
    play.className = "row-action";
    play.innerHTML = '<ha-icon icon="mdi:play-circle-outline"></ha-icon><span>Riproduci</span>';
    play.disabled = this._busy || this._loadingId === recording.recording_id;
    play.addEventListener("click", () => this._play(recording));
    const remove = document.createElement("button");
    remove.className = "danger row-action";
    remove.innerHTML = '<ha-icon icon="mdi:delete-outline"></ha-icon><span>Elimina</span>';
    remove.disabled = this._busy;
    remove.addEventListener("click", () => this._deleteOne(recording));
    actions.append(play, remove);
    row.append(actions);
    return row;
  }

  _playerRow(recording) {
    const row = document.createElement("tr");
    row.className = "player-row";
    const cell = document.createElement("td");
    cell.colSpan = 4;
    if (this._loadingId === recording.recording_id) {
      cell.innerHTML = '<div class="hint"><ha-icon icon="mdi:loading"></ha-icon> Caricamento audio…</div>';
    } else {
      const player = document.createElement("div");
      player.className = "player";
      this._player = document.createElement("audio");
      this._player.controls = true;
      this._player.preload = "metadata";
      this._player.src = this._mediaUrl;
      player.append(this._seekButton(-10), this._player, this._seekButton(10));
      cell.append(player);
    }
    row.append(cell);
    return row;
  }

  _seekButton(seconds) {
    const button = document.createElement("button");
    const forward = seconds > 0;
    button.className = "row-action";
    button.innerHTML = `<ha-icon icon="mdi:${forward ? "fast-forward" : "rewind"}-10"></ha-icon>`;
    button.setAttribute("aria-label", `${forward ? "Avanti" : "Indietro"} di 10 secondi`);
    button.addEventListener("click", () => {
      const limit = Number.isFinite(this._player.duration) ? this._player.duration : Infinity;
      this._player.currentTime = Math.max(0, Math.min(limit, this._player.currentTime + seconds));
    });
    return button;
  }

  async _play(recording) {
    this._releaseMedia();
    this._loadingId = recording.recording_id;
    this._render();
    try {
      const result = await this._hass.callWS({
        type: "media_bridge/ring/recordings/read",
        entry_id: this._entry.entry_id,
        recording_id: recording.recording_id,
      });
      const binary = atob(result.media_base64);
      const bytes = Uint8Array.from(binary, (character) => character.charCodeAt(0));
      this._mediaUrl = URL.createObjectURL(new Blob([bytes], { type: result.media_type }));
      this._activeId = recording.recording_id;
      this.$("status").textContent = "";
    } catch (_error) {
      this.$("status").textContent = "Riproduzione non disponibile.";
    } finally {
      this._loadingId = null;
      this._render();
      this._player?.play().catch(() => {});
    }
  }

  async _deleteOne(recording) {
    if (!window.confirm(`Eliminare la registrazione del ${this._date(recording)}?`)) return;
    if (this._activeId === recording.recording_id) this._releaseMedia();
    await this._delete("media_bridge/ring/recordings/delete", {
      recording_id: recording.recording_id,
    }, "Registrazione eliminata.");
  }

  async _deleteAll() {
    const count = this._recordings.length;
    if (!window.confirm(`Eliminare definitivamente tutte le ${count} registrazioni?`)) return;
    this._releaseMedia();
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
  _releaseMedia() {
    if (this._mediaUrl) URL.revokeObjectURL(this._mediaUrl);
    this._mediaUrl = null;
    this._activeId = null;
  }
  _date(recording) {
    return recordingDate(recording, this._hass?.locale?.language, this._hass?.config?.time_zone);
  }

  disconnectedCallback() { this._releaseMedia(); }
}

if (!customElements.get("vistoda-ring-recording-archive")) {
  customElements.define("vistoda-ring-recording-archive", RingRecordingArchive);
}
