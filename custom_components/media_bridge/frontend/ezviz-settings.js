import { copy } from "./panel-copy.js";
import { openMoreInfo } from "./panel-helpers.js";
import {
  OPTION_LABELS, infoText, isActionable, numberValue, providerLabel, saveErrorCopy, settingsSections,
} from "./ezviz-settings-model.js";

const html = (value) => String(value ?? "").replace(/[&<>"']/g, (character) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
})[character]);

const RELOAD_MS = 30000;

class VistodaEzvizSettings extends HTMLElement {
  constructor() { super(); this.attachShadow({ mode: "open" }); this._provider = []; this._draft = new Map(); }
  // Called on every HA state update: reload provider values only for a new
  // camera or after a quiet interval, so staged edits are never wiped.
  configure(hass, entry) {
    const changed = entry?.entry_id !== this._entry?.entry_id;
    this._hass = hass; this._entry = entry;
    if (changed) { this._provider = []; this._draft.clear(); this._error = false; }
    const stale = Date.now() - (this._loadedAt || 0) > RELOAD_MS;
    if (entry?.entry_id && (changed || (stale && !this._draft.size && !this._saving))) this._loadProvider();
    this._render();
  }

  async _loadProvider() {
    this._loadedAt = Date.now();
    const entryId = this._entry.entry_id;
    try {
      const result = await this._hass.callWS({ type: "media_bridge/ezviz/settings/info", entry_id: this._entry.entry_id });
      if (entryId !== this._entry?.entry_id) return;
      this._provider = result.settings || []; this._draft.clear(); this._error = false; this._render();
    } catch { if (entryId === this._entry?.entry_id) { this._provider = []; this._render(); } }
  }

  _render() {
    // Rebuilding would close an open confirmation or a native select picker.
    if (this.shadowRoot.querySelector("#confirm")?.open
      || ["SELECT", "INPUT"].includes(this.shadowRoot.activeElement?.tagName)) return;
    const opened = new Set([...this.shadowRoot.querySelectorAll("details[open]")]
      .map((item) => item.dataset.group));
    const sections = settingsSections(this._entry?.native_entities || [], this._provider);
    this.shadowRoot.innerHTML = `<style>
      :host{display:block}.group{border-top:1px solid var(--divider-color,#ffffff1f)}
      details>summary{display:flex;align-items:center;gap:12px;min-height:58px;padding:4px 2px;cursor:pointer;list-style:none}
      details>summary::-webkit-details-marker{display:none}summary ha-icon{color:var(--primary-color);--mdc-icon-size:24px}
      summary strong{flex:1}summary .chevron{color:var(--secondary-text-color);transition:transform .18s ease}
      details[open] summary .chevron{transform:rotate(90deg)}.rows{padding:0 0 10px 36px}
      button,.row{box-sizing:border-box;width:100%;min-height:48px;display:flex;align-items:center;gap:10px;text-align:left;
        color:var(--primary-text-color);background:transparent;border:0;border-top:1px solid var(--divider-color,#ffffff14);padding:8px 4px}
      button{cursor:pointer}.name{flex:1}.value{max-width:46%;color:var(--secondary-text-color);text-align:right;overflow-wrap:anywhere}
      select{min-height:40px;max-width:52%;border:1px solid var(--divider-color);border-radius:10px;padding:6px;
        color:var(--primary-text-color);background:var(--card-background-color)}
      .provider-toggle[aria-pressed="true"]{color:var(--primary-color)}.save{position:sticky;bottom:10px;margin-top:12px;
        border-radius:12px;background:var(--primary-color);color:var(--text-primary-color,#fff);justify-content:center;font-weight:750}
      dialog{max-width:360px;border:1px solid var(--divider-color);border-radius:16px;padding:20px;color:var(--primary-text-color);
        background:var(--card-background-color)}dialog::backdrop{background:#0009}.confirm-actions{display:flex;gap:8px;margin-top:18px}
      .empty{color:var(--secondary-text-color);font-size:13px;padding:0 0 12px 36px;margin:0}
      input[type=range]{flex:1;max-width:46%;accent-color:var(--primary-color)}
    </style>${this._error ? `<p class="empty" role="alert">${copy(this, this._error)}</p>` : ""}${sections.map((section) => `<details class="group" data-group="${section.key}"><summary>
      <ha-icon icon="${section.icon}"></ha-icon><strong>${copy(this, section.label)}</strong>
      <ha-icon class="chevron" icon="mdi:chevron-right"></ha-icon></summary>
      ${section.rows.length || section.provider.length ? `<div class="rows">${section.rows.map((entity) => {
        const state = this._hass?.states?.[entity.entity_id];
        const value = state && !["unknown", "unavailable"].includes(state.state)
          ? `${state.state}${state.attributes?.unit_of_measurement ? ` ${state.attributes.unit_of_measurement}` : ""}`
          : copy(this, "Non disponibile");
        const tag = isActionable(entity) ? "button" : "div";
        return `<${tag} class="row" data-entity="${html(entity.entity_id)}"><span class="name">${html(entity.name)}</span>
          <span class="value">${html(value)}</span>${isActionable(entity) ? '<ha-icon icon="mdi:chevron-right"></ha-icon>' : ""}</${tag}>`;
      }).join("")}${section.provider.map((setting) => this._providerRow(setting)).join("")}</div>`
        : `<p class="empty">${copy(this, "Non esposta da EZVIZ in Home Assistant")}</p>`}
    </details>`).join("")}${this._draft.size ? `<button class="save" id="save"><ha-icon icon="mdi:content-save"></ha-icon>
      ${copy(this, "Salva modifiche")}</button>` : ""}<dialog id="confirm"><strong>${copy(this, "Conferma modifiche EZVIZ")}</strong>
      <p>${copy(this, "Le impostazioni selezionate saranno applicate alla telecamera.")}</p><div class="confirm-actions">
      <button id="cancel">${copy(this, "Annulla")}</button><button id="apply">${copy(this, "Applica")}</button></div></dialog>`;
    this.shadowRoot.querySelectorAll("details").forEach((item) => { item.open = opened.has(item.dataset.group); });
    this.shadowRoot.querySelectorAll("button[data-entity]").forEach((button) => button.addEventListener("click", () =>
      openMoreInfo(this, button.dataset.entity)));
    this.shadowRoot.querySelectorAll("select[data-setting]").forEach((control) => control.addEventListener("change", () =>
      this._stage(control.dataset.setting, control.value)));
    this.shadowRoot.querySelectorAll("input[data-setting]").forEach((control) => control.addEventListener("change", () => {
      const value = numberValue(this._provider.find((item) => item.key === control.dataset.setting) || {}, control.value);
      if (value !== null) this._stage(control.dataset.setting, value);
    }));
    this.shadowRoot.querySelectorAll("button.provider-toggle").forEach((control) => control.addEventListener("click", () =>
      this._stage(control.dataset.setting, control.getAttribute("aria-pressed") !== "true")));
    this.shadowRoot.querySelector("#save")?.addEventListener("click", () => this.shadowRoot.querySelector("#confirm").showModal());
    this.shadowRoot.querySelector("#cancel")?.addEventListener("click", () => this.shadowRoot.querySelector("#confirm").close());
    this.shadowRoot.querySelector("#apply")?.addEventListener("click", () => this._save());
  }

  _providerRow(setting) {
    const value = this._draft.has(setting.key) ? this._draft.get(setting.key) : setting.value;
    const label = copy(this, providerLabel(setting.key));
    // Read-only provider state (e.g. the alarm schedule) is shown, never staged.
    if (setting.kind === "status") return `<div class="row" data-status="${setting.key}"><span class="name">${label}</span>
      <span class="value">${copy(this, value ? "Attivata" : "Disattivata")}</span></div>`;
    if (setting.kind === "info") return `<div class="row" data-status="${html(setting.key)}"><span class="name">${html(label)}</span>
      <span class="value">${html(copy(this, infoText(setting)))}</span></div>`;
    if (setting.kind === "number") return `<label class="row"><span class="name">${html(label)}</span>
      <input type="range" data-setting="${html(setting.key)}" min="${Number(setting.min)}" max="${Number(setting.max)}" step="1"
        value="${Number(value)}" aria-valuetext="${Number(value)}"><span class="value">${Number(value)}</span></label>`;
    if (setting.kind === "select") return `<label class="row"><span class="name">${label}</span><select data-setting="${setting.key}">
      ${setting.options.map((option) => `<option value="${option}"${option === value ? " selected" : ""}>${copy(this, OPTION_LABELS[option] || option)}</option>`).join("")}</select></label>`;
    return `<button class="row provider-toggle" data-setting="${setting.key}" aria-pressed="${value}"><span class="name">${label}</span>
      <ha-icon icon="${value ? "mdi:toggle-switch" : "mdi:toggle-switch-off-outline"}"></ha-icon></button>`;
  }

  _stage(key, value) { this.shadowRoot.activeElement?.blur?.(); this._draft.set(key, value); this._render(); }
  async _save() {
    this.shadowRoot.querySelector("#confirm")?.close();
    this._saving = true;
    try {
      for (const [key, value] of this._draft) {
        const original = this._provider.find((item) => item.key === key);
        const result = await this._hass.callWS({ type: "media_bridge/ezviz/settings/set", entry_id: this._entry.entry_id,
          key, value, expected_value: original.value });
        this._provider = result.settings;
      }
      this._draft.clear(); this._render();
    } catch (error) {
      this._draft.clear(); await this._loadProvider(); this._error = saveErrorCopy(error?.code); this._render();
    }
    finally { this._saving = false; }
  }
}

if (!customElements.get("vistoda-ezviz-settings")) customElements.define("vistoda-ezviz-settings", VistodaEzvizSettings);
