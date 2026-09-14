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

class VistodaEzvizSettings extends HTMLElement {
  constructor() { super(); this.attachShadow({ mode: "open" }); }
  configure(hass, entry) { this._hass = hass; this._entry = entry; this._render(); }

  _render() {
    const opened = new Set([...this.shadowRoot.querySelectorAll("details[open]")]
      .map((item) => item.dataset.group));
    const entities = this._entry?.native_entities || [];
    const claimed = new Set();
    const sections = GROUPS.map(([key, icon, label, matches]) => {
      const rows = entities.filter((entity) => !claimed.has(entity.entity_id) && matches(entity));
      rows.forEach((entity) => claimed.add(entity.entity_id));
      return { key, icon, label, rows };
    });
    const remainder = entities.filter((entity) => !claimed.has(entity.entity_id));
    if (remainder.length) sections.push({ key: "other", icon: "mdi:tune", label: "Altre impostazioni", rows: remainder });
    this.shadowRoot.innerHTML = `<style>
      :host{display:block}.group{border-top:1px solid var(--divider-color,#ffffff1f)}
      details>summary{display:flex;align-items:center;gap:12px;min-height:58px;padding:4px 2px;cursor:pointer;list-style:none}
      details>summary::-webkit-details-marker{display:none}summary ha-icon{color:var(--primary-color);--mdc-icon-size:24px}
      summary strong{flex:1}summary .chevron{color:var(--secondary-text-color);transition:transform .18s ease}
      details[open] summary .chevron{transform:rotate(90deg)}.rows{padding:0 0 10px 36px}
      button,.row{box-sizing:border-box;width:100%;min-height:48px;display:flex;align-items:center;gap:10px;text-align:left;
        color:var(--primary-text-color);background:transparent;border:0;border-top:1px solid var(--divider-color,#ffffff14);padding:8px 4px}
      button{cursor:pointer}.name{flex:1}.value{max-width:46%;color:var(--secondary-text-color);text-align:right;overflow-wrap:anywhere}
      .empty{color:var(--secondary-text-color);font-size:13px;padding:0 0 12px 36px;margin:0}
    </style>${sections.map((section) => `<details class="group" data-group="${section.key}"><summary>
      <ha-icon icon="${section.icon}"></ha-icon><strong>${copy(this, section.label)}</strong>
      <ha-icon class="chevron" icon="mdi:chevron-right"></ha-icon></summary>
      ${section.rows.length ? `<div class="rows">${section.rows.map((entity) => {
        const state = this._hass?.states?.[entity.entity_id];
        const value = state && !["unknown", "unavailable"].includes(state.state)
          ? `${state.state}${state.attributes?.unit_of_measurement ? ` ${state.attributes.unit_of_measurement}` : ""}`
          : copy(this, "Non disponibile");
        const tag = isActionable(entity) ? "button" : "div";
        return `<${tag} class="row" data-entity="${html(entity.entity_id)}"><span class="name">${html(entity.name)}</span>
          <span class="value">${html(value)}</span>${isActionable(entity) ? '<ha-icon icon="mdi:chevron-right"></ha-icon>' : ""}</${tag}>`;
      }).join("")}</div>` : `<p class="empty">${copy(this, "Non esposta da EZVIZ in Home Assistant")}</p>`}
    </details>`).join("")}`;
    this.shadowRoot.querySelectorAll("details").forEach((item) => { item.open = opened.has(item.dataset.group); });
    this.shadowRoot.querySelectorAll("button[data-entity]").forEach((button) => button.addEventListener("click", () =>
      openMoreInfo(this, button.dataset.entity)));
  }
}

if (!customElements.get("vistoda-ezviz-settings")) customElements.define("vistoda-ezviz-settings", VistodaEzvizSettings);
