import { copy, localizeCopy } from "./panel-copy.js";
import { panelLanguage } from "./panel-localize.js";
import { bindPageSize, renderPageSize } from "./archive-page-size.js";
import { alarmPage, alarmRows, MAX_LOADED_ALARMS, signedFresh } from "./ezviz-alarm-model.js";
import { alarmsTemplate } from "./ezviz-alarms-template.js";
import "./ezviz-alarm-dialog.js";

// Paged alarm list for one EZVIZ camera entry. With the event archive enabled
// it pages the archive on the server; otherwise the app answers 50 alarms at a
// time, newest first, and older batches are fetched only when a page needs them.
class VistodaEzvizAlarms extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    // The modal outlives re-renders of the list (a new alarm while it is open).
    this.shadowRoot.innerHTML = '<div id="content"></div><vistoda-ezviz-alarm-dialog id="dialog"></vistoda-ezviz-alarm-dialog>';
    this.addEventListener("alarm-open", ({ detail }) => this.shadowRoot.getElementById("dialog").open(this._hass, {
      entryId: this._entryId, alias: this._alias, rows: detail.rows, index: detail.index, pager: this._pager(), sceneTrove: this._sceneTrove, archived: Boolean(this._archive),
    }));
    // A deleted archived event leaves the list: reload from the first page.
    this.addEventListener("alarm-deleted", () => this._load());
    Object.assign(this, {
      _entryId: "", _alias: "", _token: null, _alarms: [], _rows: [], _older: null, _generation: null,
      _archive: null, _page: 1, _pageSize: 10, _busy: false, _state: "idle", _pictures: new Map(),
      _request: 0, _language: "",
    });
  }

  // The token is the alarm entity state: a change means a new alarm arrived.
  configure(hass, entry, token = null) {
    this._hass = hass;
    const entryId = entry?.entry_id || "";
    this._alias = entry?.alias || "";
    this._sceneTrove = entry?.scenetrove_url
      ? { url: entry.scenetrove_url, device: entry.scenetrove_device, shared: entry.scenetrove_shared } : null;
    const language = panelLanguage(hass);
    if (entryId !== this._entryId) {
      this._entryId = entryId;
      this._token = token;
      this._alarms = [];
      this._rows = [];
      this._older = null;
      this._generation = null;
      this._archive = null;
      this._page = 1;
      this._pictures = new Map();
      this._state = entryId ? "loading" : "idle";
      if (entryId) this._load();
      else this._render();
    } else if (entryId && token !== this._token) {
      this._token = token;
      this._load();
    } else if (language !== this._language) {
      this._render();
    }
  }

  // Newest batch: a new alarm or a manual refresh restarts from page 1.
  async _load() {
    const request = ++this._request;
    const entryId = this._entryId;
    if (!this._rows.length) this._state = "loading";
    this._busy = true;
    this._render();
    try {
      const archived = await this._archivePage(entryId, 1).catch(() => null);
      if (request !== this._request) return;
      this._showArchive(archived);
      if (!archived) {
        const result = await this._list(entryId);
        if (request !== this._request) return;
        this._accept(result, true);
      }
      this._page = 1;
    } catch {
      if (request !== this._request) return;
      this._alarms = [];
      this._rows = [];
      this._older = null;
      this._state = "error";
    }
    this._busy = false;
    this._render();
    this._signPictures(request);
  }

  // One archive page; null when the entry has not opted in to the archive.
  // Callers apply it only after checking that their request is still current.
  async _archivePage(entryId, page) {
    const result = await this._hass.callWS({
      type: "media_bridge/events/list", entry_id: entryId, page, page_size: this._pageSize,
    });
    return result?.enabled ? result : null;
  }

  _showArchive(result) {
    this._archive = result?.pagination ?? null;
    if (!result) return;
    this._rows = alarmRows(result.items, this._pageSize);
    this._state = this._rows.length ? "ready" : "empty";
  }

  _list(entryId, before = null) {
    const message = { type: "media_bridge/ezviz/alarms/list", entry_id: entryId };
    if (before !== null) Object.assign(message, { before, generation: this._generation });
    return this._hass.callWS(message);
  }

  // Keeps the batch; an older batch is appended unless the app restarted.
  _accept(result, replace) {
    const supported = result?.supported !== false;
    const fresh = supported ? (result?.alarms || []) : [];
    if (replace || result?.reset) this._alarms = fresh;
    else {
      const known = new Set(this._alarms.map((item) => item?.alarm_id));
      this._alarms = this._alarms.concat(fresh.filter((item) => !known.has(item?.alarm_id)));
    }
    this._alarms = this._alarms.slice(0, MAX_LOADED_ALARMS);
    this._rows = alarmRows(this._alarms, MAX_LOADED_ALARMS);
    this._older = supported && this._rows.length < MAX_LOADED_ALARMS && Number.isSafeInteger(result?.older)
      ? result.older : null;
    this._generation = typeof result?.generation === "string" ? result.generation : this._generation;
    this._state = !supported ? "unsupported" : this._rows.length ? "ready" : "empty";
    return Boolean(result?.reset);
  }

  // Fetches older batches until the requested page is filled or none remain.
  async _go(page) {
    if (page < 1 || this._busy) return;
    const request = ++this._request;
    const entryId = this._entryId;
    this._busy = true;
    this._page = page;
    this._render();
    try {
      if (this._archive) {
        const archived = await this._archivePage(entryId, page);
        if (request !== this._request) return;
        this._showArchive(archived);
      }
      while (!this._archive && this._older !== null && alarmPage(this._rows, page, this._pageSize, false).needsMore) {
        const result = await this._list(entryId, this._older);
        if (request !== this._request) return;
        if (this._accept(result, false)) { this._page = 1; break; }
      }
    } catch {
      if (request !== this._request) return;
      this._older = null;
    }
    this._busy = false;
    this._render();
    this._signPictures(request);
  }

  async _signPictures(request) {
    const visible = this._view().rows;
    const stale = visible.filter((row) => row.picture && !signedFresh(this._pictures.get(row.id)));
    await Promise.all(stale.map(async (row) => {
      try {
        const signed = await this._hass.callWS({ type: "auth/sign_path", path: row.picture, expires: 900 });
        if (request !== this._request || typeof signed?.path !== "string") return;
        const url = this._hass.hassUrl ? this._hass.hassUrl(signed.path) : signed.path;
        this._pictures.set(row.id, { url, at: Date.now() });
        this._showPicture(row.id);
      } catch { /* The row keeps its category icon. */ }
    }));
  }

  _showPicture(id) {
    const url = this._pictures.get(id)?.url;
    for (const thumb of this.shadowRoot.querySelectorAll("span.thumb")) {
      if (thumb.dataset.id !== id || !url) continue;
      thumb.hidden = false;
      thumb.querySelector("img").src = url;
      thumb.nextElementSibling.hidden = true;
    }
  }

  // Lets the modal step past the first or last event of the shown page.
  _pager() {
    return {
      has: (step) => (step < 0 ? this._view().hasPrevious : this._view().hasNext),
      load: async (step) => {
        const before = this._view().page;
        await this._go(before + step);
        const view = this._view();
        return view.page === before ? null : view.rows;
      },
    };
  }

  _view() {
    const archive = this._archive;
    return archive
      ? { rows: this._rows, page: archive.page, totalPages: archive.total_pages,
        hasPrevious: archive.has_previous, hasNext: archive.has_next }
      : alarmPage(this._rows, this._page, this._pageSize, this._older === null);
  }

  // Rows open the event modal (click, Enter or Space).
  _bindRows(view) {
    for (const row of this.shadowRoot.querySelectorAll("li[role=button]")) {
      const open = (event) => {
        if (event.type === "keydown" && event.key !== "Enter" && event.key !== " ") return;
        event.preventDefault();
        this.dispatchEvent(new CustomEvent("alarm-open", {
          detail: { rows: view.rows, index: Number(row.dataset.index) },
        }));
      };
      row.addEventListener("click", open);
      row.addEventListener("keydown", open);
    }
  }

  _render() {
    this._language = panelLanguage(this._hass);
    const view = this._view();
    this._page = view.page;
    const locale = this._hass?.locale?.language || "it-IT";
    const status = {
      loading: copy(this, "Caricamento…"),
      empty: copy(this, "Nessun evento recente."),
      error: copy(this, "Eventi non disponibili. Riprova più tardi."),
      unsupported: copy(this, "Aggiorna l’app Vistoda EZVIZ per ricevere gli eventi."),
    }[this._state];
    this.shadowRoot.getElementById("content").innerHTML = alarmsTemplate(this, {
      view, status, busy: this._busy, entryId: this._entryId, hasRows: this._rows.length > 0, locale,
    });
    localizeCopy(this.shadowRoot, this);
    this.shadowRoot.getElementById("reload").addEventListener("click", () => this._load());
    this.shadowRoot.getElementById("previous").addEventListener("click", () => this._go(this._page - 1));
    this.shadowRoot.getElementById("next").addEventListener("click", () => this._go(this._page + 1));
    bindPageSize(this.shadowRoot, (size) => { this._pageSize = size; this._go(1); });
    renderPageSize(this.shadowRoot, this._pageSize, this._busy, this._language);
    this._bindRows(view);
    for (const id of this._pictures.keys()) this._showPicture(id);
  }
}

if (!customElements.get("vistoda-ezviz-alarms")) {
  customElements.define("vistoda-ezviz-alarms", VistodaEzvizAlarms);
}
