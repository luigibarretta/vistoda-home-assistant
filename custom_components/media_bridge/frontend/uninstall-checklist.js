import { copy, localizeCopy } from "./panel-copy.js";
import { PROVIDER_META } from "./panel-helpers.js";
import { checklistSections } from "./uninstall-checklist-model.js";

const ICONS = { ok: "mdi:check-circle-outline", warn: "mdi:alert-circle-outline", todo: "mdi:checkbox-blank-circle-outline" };
const STATE_TEXT = { ok: "Verificato", warn: "Da controllare", todo: "Da fare" };

// Collapsible, static guidance; the outer <details> survives state updates.
class VistodaUninstallChecklist extends HTMLElement {
  constructor() { super(); this.attachShadow({ mode: "open" }); }
  set hass(value) { this._hass = value; this._render(); }
  set info(value) { this._info = value; this._render(); }

  _mount() {
    this.shadowRoot.innerHTML = `<style>
      :host{display:block;margin-top:16px}:host([hidden]){display:none}details{border:1px solid var(--divider-color);border-radius:22px;
        background:var(--card-background-color);padding:0 20px}
      summary{display:flex;align-items:center;gap:12px;min-height:56px;cursor:pointer;list-style:none;font-weight:650}
      summary::-webkit-details-marker{display:none}summary ha-icon{color:var(--primary-color)}
      summary span{flex:1}.chevron{transition:transform .18s ease}details[open] .chevron{transform:rotate(90deg)}
      @media(prefers-reduced-motion:reduce){.chevron{transition:none}}
      .intro{margin:0 0 12px;color:var(--secondary-text-color);line-height:1.45}
      h3{margin:16px 0 6px;font-size:16px}ul{list-style:none;margin:0 0 12px;padding:0}
      li{display:flex;gap:10px;align-items:flex-start;padding:8px 0;border-top:1px solid var(--divider-color);line-height:1.4}
      li ha-icon{flex:none;color:var(--secondary-text-color)}li.ok ha-icon{color:var(--success-color,#43a047)}
      li.warn ha-icon{color:var(--warning-color,#ffa600)}.note{display:block;color:var(--secondary-text-color);font-size:13px}
      .sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
    </style><details id="checklist"><summary><ha-icon icon="mdi:clipboard-check-outline"></ha-icon>
      <span data-copy="Prima di disinstallare l’app ufficiale">Prima di disinstallare l’app ufficiale</span>
      <ha-icon class="chevron" icon="mdi:chevron-right"></ha-icon></summary>
      <p class="intro" data-copy="Controlli consigliati per non perdere funzioni quando rimuovi l’app del produttore.">
        Controlli consigliati per non perdere funzioni quando rimuovi l’app del produttore.</p>
      <div id="sections"></div></details>`;
    this._mounted = true;
  }

  _render() {
    if (!this._mounted) this._mount();
    localizeCopy(this.shadowRoot, this);
    const sections = checklistSections(this._info, this._hass?.states);
    this.hidden = sections.length === 0;
    const nodes = sections.map(({ provider, items }) => {
      const section = document.createElement("section");
      const title = document.createElement("h3");
      title.textContent = PROVIDER_META[provider]?.label || provider;
      const list = document.createElement("ul");
      for (const item of items) {
        const row = document.createElement("li"); row.className = item.state;
        const icon = document.createElement("ha-icon"); icon.setAttribute("icon", ICONS[item.state]);
        icon.setAttribute("aria-hidden", "true");
        const text = document.createElement("span");
        const state = document.createElement("span"); state.className = "sr";
        state.textContent = `${copy(this, STATE_TEXT[item.state])}: `;
        text.append(state, copy(this, item.text));
        if (item.note) {
          const note = document.createElement("span"); note.className = "note";
          note.textContent = copy(this, item.note); text.append(note);
        }
        row.append(icon, text); list.append(row);
      }
      section.append(title, list);
      return section;
    });
    this.shadowRoot.getElementById("sections").replaceChildren(...nodes);
  }
}

if (!customElements.get("vistoda-uninstall-checklist")) {
  customElements.define("vistoda-uninstall-checklist", VistodaUninstallChecklist);
}
