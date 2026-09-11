import { copy, localizeCopy } from "./panel-copy.js";
import { BASE_STYLES } from "./panel-styles.js";

const FIELDS = [
  ["device_name", "Nome dispositivo", "mdi:door-open"],
  ["location_name", "Nome Location", "mdi:home-map-marker"],
  ["city", "Città", "mdi:city-variant-outline"],
];

export class RingIdentityDialog extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._mounted = false;
  }

  configure(hass, entry, configuration) {
    this._hass = hass;
    this._entry = entry;
    this._configuration = configuration;
    if (!this._mounted) this._mount();
    localizeCopy(this.shadowRoot, this);
  }

  show() {
    if (!this._configuration) return;
    this._renderFields();
    this.$("error").hidden = true;
    this.$("dialog").showModal();
  }

  _mount() {
    this._mounted = true;
    this.shadowRoot.innerHTML = `
      <style>${BASE_STYLES}
        dialog{width:min(520px,calc(100vw - 28px));max-height:calc(100vh - 36px);padding:0;
          border:1px solid var(--divider-color);border-radius:18px;color:var(--primary-text-color);
          background:var(--card-background-color);box-shadow:0 22px 70px #0008;overflow:auto}
        dialog::backdrop{background:#0009}.head{display:flex;gap:12px;align-items:center;padding:19px 20px;
          border-bottom:1px solid var(--divider-color)}.head ha-icon{color:var(--primary-color)}
        h2{font-size:21px;margin:0}.intro{margin:0;padding:14px 20px 2px;color:var(--secondary-text-color);
          font-size:13px;line-height:1.45}.fields{padding:7px 20px 4px}.field{padding:15px 0;
          border-bottom:1px solid var(--divider-color)}.field:last-child{border:0}.field-title{display:flex;
          align-items:center;gap:9px;font-weight:700;margin-bottom:10px}.field-title ha-icon{
          --mdc-icon-size:20px;color:var(--primary-color)}.inputs{display:grid;grid-template-columns:1fr 1fr;
          gap:10px}select,input{box-sizing:border-box;min-height:44px;width:100%;border:1px solid
          var(--divider-color);border-radius:11px;padding:9px 11px;background:var(--secondary-background-color);
          color:var(--primary-text-color);font:inherit}.source-value{margin:8px 1px 0;color:var(--secondary-text-color);
          font-size:12px;overflow-wrap:anywhere}.actions{display:flex;justify-content:flex-end;gap:10px;
          padding:16px 20px;border-top:1px solid var(--divider-color)}.actions button{display:inline-flex;
          align-items:center;gap:7px;min-height:44px}.error{margin:0;padding:0 20px 12px;color:var(--error-color)}
        @media(max-width:520px){dialog{width:calc(100vw - 20px);max-height:calc(100vh - 20px)}
          .head,.fields,.actions{padding-left:15px;padding-right:15px}.intro{padding-left:15px;
          padding-right:15px}.inputs{grid-template-columns:1fr}}
      </style>
      <dialog id="dialog" aria-labelledby="identity-title"><header class="head"><ha-icon icon="mdi:account-edit-outline"></ha-icon>
        <h2 id="identity-title"><span data-copy="Identità Ring">Identità Ring</span></h2></header><p class="intro"><span data-copy="Scegli separatamente la sorgente di ogni nome. Home Assistant espone il nome del dispositivo e quello dell’installazione, ma non conserva la città come campo strutturato.">Scegli separatamente la sorgente di ogni
        nome. Home Assistant espone il nome del dispositivo e quello dell’installazione, ma non
        conserva la città come campo strutturato.</span></p><form id="form"><div class="fields" id="fields">
        </div><p class="error" id="error" role="alert" hidden></p><footer class="actions">
          <button type="button" id="cancel"><ha-icon icon="mdi:close"></ha-icon><span data-copy="Annulla">Annulla</span></button>
          <button type="submit" class="primary" id="save"><ha-icon icon="mdi:content-save-outline">
          </ha-icon><span data-copy="Salva">Salva</span></button></footer></form></dialog>`; localizeCopy(this.shadowRoot, this);
    this.$ = (id) => this.shadowRoot.getElementById(id);
    this.$("cancel").addEventListener("click", () => this.$("dialog").close());
    this.$("form").addEventListener("submit", (event) => this._save(event));
  }

  _renderFields() {
    const { selection, custom, available } = this._configuration;
    const nodes = FIELDS.map(([key, sourceLabel, icon]) => {
      const label = copy(this, sourceLabel);
      const section = document.createElement("section"); section.className = "field";
      section.innerHTML = `<div class="field-title"><ha-icon icon="${icon}"></ha-icon>
        <span></span></div><div class="inputs"><select>
        <option value="ring">Ring</option>${key === "city" ? "" :
    '<option value="home_assistant">Home Assistant</option>'}
        <option value="custom" data-copy="Personalizzato">Personalizzato</option></select><input maxlength="128">
        </div><p class="source-value"></p>`; localizeCopy(section, this);
      section.querySelector(".field-title span").textContent = label;
      const select = section.querySelector("select"); const input = section.querySelector("input");
      select.setAttribute("aria-label", copy(this, "Sorgente {p0}", { p0: label }));
      input.setAttribute("aria-label", copy(this, "Valore personalizzato {p0}", { p0: label }));
      input.placeholder = copy(this, "Inserisci {p0}", { p0: label.toLowerCase() });
      select.value = selection[key]; input.value = custom[key] || "";
      const update = () => {
        input.hidden = select.value !== "custom";
        const source = select.value === "home_assistant" ? "home_assistant" : "ring";
        const current = available[source]?.[key] || copy(this, "Non impostato");
        section.querySelector(".source-value").textContent = select.value === "custom"
          ? copy(this, "Il valore personalizzato verrà usato in cronologia e notifiche.")
          : copy(this, "Valore disponibile: {p0}", { p0: current });
      };
      select.dataset.field = key; input.dataset.field = key;
      select.addEventListener("change", update); update();
      return section;
    });
    this.$("fields").replaceChildren(...nodes);
  }

  async _save(event) {
    event.preventDefault();
    const selection = {}; const custom = {};
    for (const [key] of FIELDS) {
      selection[key] = this.shadowRoot.querySelector(`select[data-field="${key}"]`).value;
      custom[key] = this.shadowRoot.querySelector(`input[data-field="${key}"]`).value.trim();
      if (selection[key] === "custom" && !custom[key]) {
        this.$("error").textContent = copy(this, "Compila tutti i valori impostati come personalizzati.");
        this.$("error").hidden = false; return;
      }
    }
    this.$("save").disabled = true; this.$("error").hidden = true;
    try {
      const result = await this._hass.callWS({ type: "media_bridge/ring/identity/update",
        entry_id: this._entry.entry_id, selection, custom });
      this._configuration = result.identity_configuration;
      this.$("dialog").close();
      this.dispatchEvent(new CustomEvent("identity-updated", {
        detail: result, bubbles: true, composed: true,
      }));
    } catch (_error) {
      this.$("error").textContent = copy(this, "Impossibile salvare l’identità Ring.");
      this.$("error").hidden = false;
    } finally { this.$("save").disabled = false; }
  }
}

if (!customElements.get("vistoda-ring-identity-dialog")) {
  customElements.define("vistoda-ring-identity-dialog", RingIdentityDialog);
}
