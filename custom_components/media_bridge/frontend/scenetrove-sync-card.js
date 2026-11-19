// SceneTrove's cloud microSD sync for this camera, on the EZVIZ details page.
// SceneTrove owns and runs the schedule; administrators change it here.
import { copy, localizeCopy } from "./panel-copy.js";
import { panelLanguage } from "./panel-localize.js";
import {
  batteryPowered, errorLabel, resultLabel, scheduleFor, syncChoice, syncChoices, syncNotice,
} from "./scenetrove-sync-model.js";

const RELOAD_MS = 60000;
const html = (value) => String(value ?? "").replace(/[&<>"']/g, (character) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
})[character]);

class VistodaSceneTroveSync extends HTMLElement {
  constructor() { super(); this.attachShadow({ mode: "open" }); this._request = 0; }

  configure(hass, entry) {
    const changed = entry?.entry_id !== this._entry?.entry_id || entry?.scenetrove_url !== this._entry?.scenetrove_url;
    this._hass = hass; this._entry = entry;
    this.hidden = !entry?.scenetrove_url;
    if (this.hidden) return;
    if (changed) { this._state = "loading"; this._sync = null; this._error = ""; this._render(); }
    if (changed || (Date.now() - (this._loadedAt || 0) > RELOAD_MS && !this._saving)) this._load();
  }

  async _load() {
    this._loadedAt = Date.now();
    const request = ++this._request;
    try {
      const result = await this._hass.callWS({ type: "media_bridge/ezviz/sd_sync/info", entry_id: this._entry.entry_id });
      if (request !== this._request) return;
      this._sync = result.sync; this._state = result.sync ? "ready" : "unlinked"; this._error = "";
    } catch (error) {
      if (request !== this._request) return;
      this._state = "error"; this._error = errorLabel(error?.code);
    }
    this._render();
  }

  async _save(choice) {
    const schedule = scheduleFor(choice, this._sync, this._entry);
    if (!schedule) return;
    this._saving = true; this._error = ""; this._render();
    const request = ++this._request;
    try {
      const result = await this._hass.callWS({ type: "media_bridge/ezviz/sd_sync/set", entry_id: this._entry.entry_id, ...schedule });
      if (request === this._request) this._sync = result.sync;
    } catch (error) {
      if (request === this._request) this._error = errorLabel(error?.code);
    } finally {
      this._saving = false; this._loadedAt = Date.now(); this._render();
    }
  }

  _time(value) {
    const date = value ? new Date(value) : null;
    if (!date || Number.isNaN(date.getTime())) return "—";
    const locale = panelLanguage(this._hass) === "it" ? "it-IT" : (this._hass?.locale?.language || "en");
    return new Intl.DateTimeFormat(locale, { dateStyle: "short", timeStyle: "short" }).format(date);
  }

  _body() {
    if (this._state === "loading") return `<p class="muted" role="status">${copy(this, "Caricamento…")}</p>`;
    if (this._state === "unlinked") return `<p class="muted">${copy(this, "Per vedere e cambiare la sincronizzazione da qui, aggiungi un token SceneTrove con lo scope devices:sd-sync nelle opzioni dell’integrazione Vistoda.")}</p>`;
    if (this._state === "error") return `<p class="error" role="alert">${html(copy(this, this._error))}</p>
      <button id="retry">${copy(this, "Riprova")}</button>`;
    const sync = this._sync;
    const admin = Boolean(this._hass?.user?.is_admin);
    const current = syncChoice(sync);
    const options = syncChoices(sync).map((option) => `<option value="${option.value}"${option.value === current ? " selected" : ""}>${
      html(copy(this, option.label, option.values))}</option>`).join("");
    const last = sync.last;
    const notice = syncNotice(sync);
    return `<label class="row"><span class="name">${copy(this, "Copia le clip della microSD")}</span>
        <select id="interval"${admin && !this._saving ? "" : " disabled"}>${options}</select></label>
      <p class="muted">${copy(this, "Più spesso: registrazioni più recenti in SceneTrove, ma più consumo di batteria.")}${
        batteryPowered(this._entry) ? ` ${copy(this, "Consigliato per questa telecamera a batteria: ogni 6 ore.")}` : ""}</p>
      ${this._saving ? `<p class="muted" role="status">${copy(this, "Salvataggio…")}</p>` : ""}
      ${this._error ? `<p class="error" role="alert">${html(copy(this, this._error))}</p>` : ""}
      ${notice ? `<p class="error" role="status">${html(copy(this, notice))}</p>` : ""}
      <p class="muted">${last ? html(copy(this, "Ultima sincronizzazione: {p0}, {p1}", {
        p0: this._time(last.finished_at), p1: copy(this, resultLabel(last.result)),
      })) : copy(this, "Nessuna sincronizzazione ancora eseguita.")}</p>
      <p class="muted">${html(copy(this, "Ultima riuscita: {p0}", { p0: this._time(sync.last_success_at) }))}${
        sync.enabled ? ` · ${html(copy(this, "Prossima: {p0}", { p0: this._time(sync.next_run_at) }))}` : ""}</p>
      ${admin ? "" : `<p class="muted">${copy(this, "Solo un amministratore può cambiare la sincronizzazione.")}</p>`}`;
  }

  _render() {
    // Rebuilding would close an open native select picker.
    if (this.shadowRoot.activeElement?.tagName === "SELECT") return;
    this.shadowRoot.innerHTML = `<style>
      :host{display:block}:host([hidden]){display:none}
      section{margin-top:16px;padding:12px 16px;border:1px solid var(--divider-color);border-radius:12px}
      h3{margin:0 0 6px;font-size:15px}p{margin:6px 0 0;font-size:13px}.muted{color:var(--secondary-text-color)}
      .error{color:var(--error-color,#db4437)}.row{display:flex;align-items:center;gap:10px;min-height:48px}.name{flex:1}
      select{min-height:40px;max-width:52%;border:1px solid var(--divider-color);border-radius:10px;padding:6px;
        color:var(--primary-text-color);background:var(--card-background-color)}
      button{margin-top:8px;min-height:44px;padding:0 14px;border:0;border-radius:12px;background:transparent;
        color:var(--primary-color);cursor:pointer}button:focus-visible,select:focus-visible{outline:2px solid var(--primary-color)}
    </style><section><h3 data-copy="Sincronizzazione microSD con SceneTrove">Sincronizzazione microSD con SceneTrove</h3>${this._body()}</section>`;
    localizeCopy(this.shadowRoot, this);
    this.shadowRoot.getElementById("retry")?.addEventListener("click", () => { this._state = "loading"; this._render(); this._load(); });
    this.shadowRoot.getElementById("interval")?.addEventListener("change", (event) => {
      event.target.blur(); this._save(event.target.value);
    });
  }
}

if (!customElements.get("vistoda-scenetrove-sync")) customElements.define("vistoda-scenetrove-sync", VistodaSceneTroveSync);
