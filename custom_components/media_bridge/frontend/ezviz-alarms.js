import { copy, localizeCopy } from "./panel-copy.js";
import { panelLanguage } from "./panel-localize.js";
import { alarmIsoTime, alarmRows, alarmTimeText } from "./ezviz-alarm-model.js";

const html = (value) => String(value ?? "").replace(/[&<>"']/g, (character) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
})[character]);

// Compact recent-alarm list for one EZVIZ camera entry.
class VistodaEzvizAlarms extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._entryId = "";
    this._token = null;
    this._rows = [];
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
      this._rows = [];
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

  async _load() {
    const request = ++this._request;
    const entryId = this._entryId;
    if (!this._rows.length) this._state = "loading";
    this._render();
    try {
      const result = await this._hass.callWS({ type: "media_bridge/ezviz/alarms/list", entry_id: entryId });
      if (request !== this._request) return;
      this._rows = result?.supported === false ? [] : alarmRows(result?.alarms, 10);
      this._state = result?.supported === false ? "unsupported" : this._rows.length ? "ready" : "empty";
    } catch {
      if (request !== this._request) return;
      this._rows = [];
      this._state = "error";
    }
    this._render();
    this._signPictures(request);
  }

  async _signPictures(request) {
    await Promise.all(this._rows.filter((row) => row.picture && !this._pictures.has(row.id)).map(async (row) => {
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

  _render() {
    this._language = panelLanguage(this._hass);
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
    </style><div class="head"><h3 data-copy="Eventi">Eventi</h3>
      <button id="reload" aria-label="Aggiorna eventi" title="Aggiorna eventi" data-copy-aria-label="Aggiorna eventi"
        data-copy-title="Aggiorna eventi" ${this._entryId ? "" : "disabled"}><ha-icon icon="mdi:refresh"></ha-icon></button></div>
      ${status ? `<p class="status" role="status">${html(status)}</p>` : ""}
      <ul aria-label="${html(copy(this, "Eventi"))}">${this._rows.map((row) => `<li>
        <a class="thumb" data-id="${html(row.id)}" target="_blank" rel="noopener" hidden>
          <img alt="${html(copy(this, "Immagine evento: {p0}", { p0: copy(this, row.label) }))}" loading="lazy"></a>
        <span class="icon" aria-hidden="true"><ha-icon icon="${html(row.icon)}"></ha-icon></span>
        <span class="text"><strong>${html(copy(this, row.label))}</strong>
          ${row.title ? `<span class="title">${html(row.title)}</span>` : ""}</span>
        <time datetime="${html(alarmIsoTime(row.occurredAt))}">${html(alarmTimeText(row.occurredAt, locale))}</time></li>`).join("")}</ul>`;
    localizeCopy(this.shadowRoot, this);
    this.shadowRoot.getElementById("reload").addEventListener("click", () => this._load());
    for (const id of this._pictures.keys()) this._showPicture(id);
  }
}

if (!customElements.get("vistoda-ezviz-alarms")) {
  customElements.define("vistoda-ezviz-alarms", VistodaEzvizAlarms);
}
