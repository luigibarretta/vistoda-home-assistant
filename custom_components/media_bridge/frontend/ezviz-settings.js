import { copy } from "./panel-copy.js";
import { openMoreInfo } from "./panel-helpers.js";

const GROUPS = [
  ["battery", "mdi:battery", "Batteria", (e) => e.device_class === "battery"],
  ["detection", "mdi:motion-sensor", "Rilevamento intelligente", (e) =>
    e.entity_id.includes("motion") || e.entity_id.includes("detection") || e.entity_id.includes("pir")],
  ["notifications", "mdi:bell-outline", "Notifiche", (e) =>
    e.entity_id.includes("notification") || e.entity_id.includes("alarm_notify")],
  ["audio", "mdi:microphone-outline", "Audio", (e) =>
    e.entity_id.includes("audio") || e.entity_id.includes("volume") || e.entity_id.includes("sound")],
  ["image", "mdi:image-outline", "Immagine", (e) =>
    e.entity_id.includes("image") || e.entity_id.includes("night") || e.entity_id.includes("infrared")],
  ["light", "mdi:lightbulb-outline", "Luci", (e) =>
    e.domain === "light" || e.entity_id.includes("light") || e.entity_id.includes("led")],
  ["privacy", "mdi:shield-outline", "Privacy", (e) =>
    e.entity_id.includes("privacy") || e.entity_id.includes("sleep")],
  ["network", "mdi:wifi", "Rete", (e) =>
    e.entity_id.includes("wifi") || e.entity_id.includes("signal") || e.device_class === "signal_strength"],
  ["device", "mdi:information-outline", "Informazioni dispositivo", (e) =>
    e.domain === "update" || e.entity_id.includes("firmware")],
];

const isActionable = (entity) => ["switch", "select", "number", "button", "light"].includes(entity.domain);
const html = (value) => String(value ?? "").replace(/[&<>"']/g, (character) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
})[character]);

const PROVIDER_LABELS = {
  battery_work_mode: "Modalità di lavoro", receive_device_message: "Ricevi messaggi dispositivo",
  answer_doorbell_call: "Rispondi alle chiamate citofono", offline_notification: "Notifica dispositivo offline",
  human_detection: "Rilevamento sagoma umana", wide_dynamic_range: "WDR",
  distortion_correction: "Correzione distorsione", logo_watermark: "Filigrana logo",
};
const OPTION_LABELS = { power_saving: "Risparmio energetico", high_performance: "Prestazioni elevate",
  super_power_saving: "Super risparmio energetico", user_customization: "Personalizzazione utente" };

class VistodaEzvizSettings extends HTMLElement {
  constructor() { super(); this.attachShadow({ mode: "open" }); this._provider = []; this._draft = new Map(); }
  configure(hass, entry) {
    this._hass = hass; this._entry = entry; this._render();
    if (entry?.entry_id) this._loadProvider();
  }

  async _loadProvider() {
    try {
      const result = await this._hass.callWS({ type: "media_bridge/ezviz/settings/info", entry_id: this._entry.entry_id });
      this._provider = result.settings || []; this._draft.clear(); this._error = false; this._render();
    } catch { this._provider = []; this._render(); }
  }

  _render() {
    const opened = new Set([...this.shadowRoot.querySelectorAll("details[open]")]
      .map((item) => item.dataset.group));
    const entities = this._entry?.native_entities || [];
    const claimed = new Set();
    const sections = GROUPS.map(([key, icon, label, matches]) => {
      const rows = entities.filter((entity) => !claimed.has(entity.entity_id) && matches(entity));
      rows.forEach((entity) => claimed.add(entity.entity_id));
      return { key, icon, label, rows, provider: this._provider.filter((item) => item.group === key) };
    });
    const remainder = entities.filter((entity) => !claimed.has(entity.entity_id));
    if (remainder.length) sections.push({ key: "other", icon: "mdi:tune", label: "Altre impostazioni", rows: remainder, provider: [] });
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
    </style>${this._error ? `<p class="empty" role="alert">${copy(this, "Impossibile applicare le impostazioni EZVIZ.")}</p>` : ""}${sections.map((section) => `<details class="group" data-group="${section.key}"><summary>
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
    this.shadowRoot.querySelectorAll("[data-setting]").forEach((control) => control.addEventListener("change", () =>
      this._stage(control.dataset.setting, control.tagName === "SELECT" ? control.value : control.getAttribute("aria-pressed") !== "true")));
    this.shadowRoot.querySelectorAll("button.provider-toggle").forEach((control) => control.addEventListener("click", () =>
      this._stage(control.dataset.setting, control.getAttribute("aria-pressed") !== "true")));
    this.shadowRoot.querySelector("#save")?.addEventListener("click", () => this.shadowRoot.querySelector("#confirm").showModal());
    this.shadowRoot.querySelector("#cancel")?.addEventListener("click", () => this.shadowRoot.querySelector("#confirm").close());
    this.shadowRoot.querySelector("#apply")?.addEventListener("click", () => this._save());
  }

  _providerRow(setting) {
    const value = this._draft.has(setting.key) ? this._draft.get(setting.key) : setting.value;
    const label = copy(this, PROVIDER_LABELS[setting.key] || setting.key);
    if (setting.kind === "select") return `<label class="row"><span class="name">${label}</span><select data-setting="${setting.key}">
      ${setting.options.map((option) => `<option value="${option}"${option === value ? " selected" : ""}>${copy(this, OPTION_LABELS[option] || option)}</option>`).join("")}</select></label>`;
    return `<button class="row provider-toggle" data-setting="${setting.key}" aria-pressed="${value}"><span class="name">${label}</span>
      <ha-icon icon="${value ? "mdi:toggle-switch" : "mdi:toggle-switch-off-outline"}"></ha-icon></button>`;
  }

  _stage(key, value) { this._draft.set(key, value); this._render(); }
  async _save() {
    this.shadowRoot.querySelector("#confirm")?.close();
    try {
      for (const [key, value] of this._draft) {
        const original = this._provider.find((item) => item.key === key);
        const result = await this._hass.callWS({ type: "media_bridge/ezviz/settings/set", entry_id: this._entry.entry_id,
          key, value, expected_value: original.value });
        this._provider = result.settings;
      }
      this._draft.clear(); this._render();
    } catch { this._draft.clear(); await this._loadProvider(); this._error = true; this._render(); }
  }
}

if (!customElements.get("vistoda-ezviz-settings")) customElements.define("vistoda-ezviz-settings", VistodaEzvizSettings);
