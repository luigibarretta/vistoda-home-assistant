import { copy, localizeCopy } from "./panel-copy.js";
import { panelLanguage } from "./panel-localize.js";
import { bindPageSize, PAGE_SIZE_TEMPLATE, renderPageSize } from "./archive-page-size.js";
import { alarmIsoTime, alarmPage, alarmRows, alarmTimeText, MAX_LOADED_ALARMS } from "./ezviz-alarm-model.js";

const html = (value) => String(value ?? "").replace(/[&<>"']/g, (character) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
})[character]);

// Paged alarm list for one EZVIZ camera entry. The app answers 50 alarms at
// a time, newest first; older batches are fetched only when a page needs them.
class VistodaEzvizAlarms extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._entryId = "";
    this._token = null;
    this._alarms = [];
    this._rows = [];
    this._older = null;
    this._generation = null;
    this._page = 1;
    this._pageSize = 10;
    this._busy = false;
    this._state = "idle";
    this._pictures = new Map();
    this._request = 0;
    this._language = "";
  }

  // The token is the alarm entity state: a change means a new alarm arrived.
  configure(hass, entry, token = null) {
    this._hass = hass;
    const entryId = entry?.entry_id || "";
    const language = panelLanguage(hass);
    if (entryId !== this._entryId) {
      this._entryId = entryId;
      this._token = token;
      this._alarms = [];
      this._rows = [];
      this._older = null;
      this._generation = null;
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
      const result = await this._list(entryId);
      if (request !== this._request) return;
      this._accept(result, true);
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
      while (this._older !== null && alarmPage(this._rows, page, this._pageSize, false).needsMore) {
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
    await Promise.all(visible.filter((row) => row.picture && !this._pictures.has(row.id)).map(async (row) => {
      try {
        const signed = await this._hass.callWS({ type: "auth/sign_path", path: row.picture, expires: 900 });
        if (request !== this._request || typeof signed?.path !== "string") return;
        this._pictures.set(row.id, this._hass.hassUrl ? this._hass.hassUrl(signed.path) : signed.path);
        this._showPicture(row.id);
      } catch { /* The row keeps its category icon. */ }
    }));
  }

  _showPicture(id) {
    const url = this._pictures.get(id);
    for (const link of this.shadowRoot.querySelectorAll("a.thumb")) {
      if (link.dataset.id !== id || !url) continue;
      link.href = url;
      link.hidden = false;
      link.querySelector("img").src = url;
      link.nextElementSibling.hidden = true;
    }
  }

  _view() {
    return alarmPage(this._rows, this._page, this._pageSize, this._older === null);
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
    this.shadowRoot.innerHTML = `<style>
      :host{display:block;margin-top:14px}[hidden]{display:none!important}
      .head{display:flex;align-items:center;gap:8px}.head h3{flex:1;margin:0;font-size:16px}
      button{min-width:44px;min-height:44px;border:0;border-radius:12px;background:transparent;color:var(--primary-text-color);cursor:pointer}
      button:focus-visible,a:focus-visible{outline:2px solid var(--primary-color);outline-offset:2px}
      ul{list-style:none;margin:6px 0 0;padding:0}li{display:flex;align-items:center;gap:12px;min-height:56px;
        padding:6px 0;border-top:1px solid var(--divider-color,#ffffff1f)}
      .thumb,.icon{flex:none;width:72px;height:44px;border-radius:8px;overflow:hidden}
      .thumb img{width:100%;height:100%;object-fit:cover;display:block}
      .icon{display:grid;place-content:center;background:color-mix(in srgb,var(--primary-color) 12%,transparent);color:var(--primary-color)}
      .text{flex:1;min-width:0}.text strong{display:block}.title{color:var(--secondary-text-color);font-size:13px;overflow-wrap:anywhere}
      time{color:var(--secondary-text-color);font-size:13px;white-space:nowrap}.status{color:var(--secondary-text-color);margin:8px 0 0}
      .archive-pager{display:grid;grid-template-columns:auto 1fr auto;align-items:center;gap:10px;margin-top:12px}
      .archive-pager span{text-align:center;color:var(--secondary-text-color);font-size:13px}
      .archive-pager button{display:flex;align-items:center;gap:4px;padding:0 10px}
      .archive-pager button:disabled{opacity:.45;cursor:not-allowed}
      @media (max-width:600px){.archive-pager{grid-template-columns:1fr 1fr}.archive-pager span{grid-column:1 / -1;grid-row:1}}
    </style><div class="head"><h3 data-copy="Eventi">Eventi</h3>
      <button id="reload" aria-label="Aggiorna eventi" title="Aggiorna eventi" data-copy-aria-label="Aggiorna eventi"
        data-copy-title="Aggiorna eventi" ${this._entryId ? "" : "disabled"}><ha-icon icon="mdi:refresh"></ha-icon></button></div>
      ${status ? `<p class="status" role="status">${html(status)}</p>` : ""}
      <div ${this._rows.length ? "" : "hidden"}>${PAGE_SIZE_TEMPLATE.replace("<vistoda-page-size ", '<vistoda-page-size unit="events" ')}</div>
      <ul aria-label="${html(copy(this, "Eventi"))}">${view.rows.map((row) => `<li>
        <a class="thumb" data-id="${html(row.id)}" target="_blank" rel="noopener" hidden>
          <img alt="${html(copy(this, "Immagine evento: {p0}", { p0: copy(this, row.label) }))}" loading="lazy"></a>
        <span class="icon" aria-hidden="true"><ha-icon icon="${html(row.icon)}"></ha-icon></span>
        <span class="text"><strong>${html(copy(this, row.label))}</strong>
          ${row.title ? `<span class="title">${html(row.title)}</span>` : ""}</span>
        <time datetime="${html(alarmIsoTime(row.occurredAt))}">${html(alarmTimeText(row.occurredAt, locale))}</time></li>`).join("")}</ul>
      <nav class="archive-pager" aria-label="${html(copy(this, "Pagine eventi"))}" ${view.hasPrevious || view.hasNext ? "" : "hidden"}>
        <button id="previous" ${this._busy || !view.hasPrevious ? "disabled" : ""}><ha-icon icon="mdi:chevron-left"></ha-icon>
          <span>${html(copy(this, "Precedente"))}</span></button>
        <span id="page-label">${html(view.totalPages === null
          ? copy(this, "Pagina {p0}", { p0: view.page })
          : copy(this, "Pagina {p0} di {p1}", { p0: view.page, p1: view.totalPages }))}</span>
        <button id="next" ${this._busy || !view.hasNext ? "disabled" : ""}><span>${html(copy(this, "Successiva"))}</span>
          <ha-icon icon="mdi:chevron-right"></ha-icon></button></nav>`;
    localizeCopy(this.shadowRoot, this);
    this.shadowRoot.getElementById("reload").addEventListener("click", () => this._load());
    this.shadowRoot.getElementById("previous").addEventListener("click", () => this._go(this._page - 1));
    this.shadowRoot.getElementById("next").addEventListener("click", () => this._go(this._page + 1));
    bindPageSize(this.shadowRoot, (size) => { this._pageSize = size; this._go(1); });
    renderPageSize(this.shadowRoot, this._pageSize, this._busy, this._language);
    for (const id of this._pictures.keys()) this._showPicture(id);
  }
}

if (!customElements.get("vistoda-ezviz-alarms")) {
  customElements.define("vistoda-ezviz-alarms", VistodaEzvizAlarms);
}
