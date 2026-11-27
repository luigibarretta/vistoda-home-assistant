import { copy, localizeCopy } from "./panel-copy.js";
import { FEATURES, normalizeFeatures } from "./archive-features-model.js";

const ROWS = [
  ["usb", "USB Blink", "Clip sulla chiavetta del Sync Module e la destinazione «Archivio Blink» di REC."],
  ["local_ha", "Locale HA", "Registrazioni fatte da Vistoda (REC e movimento) nell'archivio dell'app. Spegnerlo ferma anche la registrazione al movimento."],
  ["nfs", "Backup NFS", "Copie verificate nella cartella scelta, automatiche e manuali. Spegnerlo ferma il backup automatico."],
];

/** The switches that choose which archives stay active; the panel follows `archive-features-change`. */
class ArchiveFeatures extends HTMLElement {
  constructor() {
    super(); this.attachShadow({ mode: "open" });
    this.features = normalizeFeatures(null); this.busy = false;
    this.shadowRoot.innerHTML = `<style>
      :host { display:block; margin-bottom:16px; } [hidden] { display:none !important; }
      details { border:1px solid var(--divider-color); border-radius:12px; padding:0 16px; }
      summary { min-height:48px; display:flex; align-items:center; gap:8px; cursor:pointer; font-weight:600; }
      summary .state { font-weight:400; color:var(--secondary-text-color); font-size:13px; }
      label { display:flex; gap:12px; align-items:flex-start; padding:10px 0; border-top:1px solid var(--divider-color); }
      input { width:22px; height:22px; flex:none; margin-top:2px; accent-color:var(--primary-color); }
      .text { display:block; } .hint { display:block; color:var(--secondary-text-color); font-size:13px; }
      #status { margin:0; padding:8px 0 12px; font-size:13px; color:var(--secondary-text-color); }
    </style><details><summary><span data-copy="Archivi attivi">Archivi attivi</span>
      <span class="state" id="state"></span></summary><div id="rows"></div><p id="status" role="status"></p></details>`;
    this.rows = {};
    for (const [name, label, hint] of ROWS) {
      const row = document.createElement("label"), input = document.createElement("input");
      input.type = "checkbox"; input.setAttribute("role", "switch"); input.dataset.feature = name;
      input.addEventListener("change", () => this._change(name, input.checked));
      const text = document.createElement("span"); text.className = "text";
      text.innerHTML = `<strong data-copy="${label}">${label}</strong><span class="hint" data-copy="${hint}">${hint}</span>`;
      row.append(input, text); this.rows[name] = input; this.shadowRoot.getElementById("rows").append(row);
    }
  }
  _admin() { return this._hass?.user?.is_admin === true; }
  async configure(hass, entryId) {
    this._hass = hass; this.entryId = entryId || ""; localizeCopy(this.shadowRoot, this);
    if (this._loaded || !hass) { this._render(); return; }
    this._loaded = true;
    try { this._set(await hass.callWS({ type: "media_bridge/blink/recording_options" }), false); }
    catch { this._loaded = false; }
    this._render();
  }
  _set(raw, announce = true) {
    this.features = normalizeFeatures(raw);
    this.dispatchEvent(new CustomEvent("archive-features-change", {
      detail: this.features, bubbles: true, composed: true }));
    if (announce) this._render();
  }
  async _change(name, value) {
    if (this.busy || !this._admin()) { this._render(); return; }
    this.busy = true; this._render();
    try {
      this._set(await this._hass.callWS({ type: "media_bridge/blink/archive_features/set",
        ...(this.entryId ? { entry_id: this.entryId } : {}), [name]: value }));
      this.shadowRoot.getElementById("status").textContent = "";
    } catch {
      this.shadowRoot.getElementById("status").textContent = copy(this, "Impossibile cambiare gli archivi attivi.");
    } finally { this.busy = false; this._render(); }
  }
  _render() {
    const names = { usb: "USB Blink", local_ha: "Locale HA", nfs: "Backup NFS" };
    for (const name of FEATURES) {
      this.rows[name].checked = this.features[name];
      this.rows[name].disabled = this.busy || !this._admin();
    }
    const active = FEATURES.filter((name) => this.features[name]).map((name) => copy(this, names[name]));
    this.shadowRoot.getElementById("state").textContent = active.length ? active.join(" · ") : copy(this, "nessuno");
    if (!this._admin() && this._hass) this.shadowRoot.getElementById("status").textContent =
      copy(this, "Solo un amministratore può cambiare gli archivi attivi.");
    localizeCopy(this.shadowRoot, this);
  }
}
if (!customElements.get("vistoda-archive-features")) customElements.define("vistoda-archive-features", ArchiveFeatures);
