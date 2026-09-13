import { RingCameraDialog } from "./ring-camera-dialog.js";
import { copy } from "./panel-copy.js";

// Native account inventory. Camera identities never become Intercom aliases.
class RingCameraGallery extends HTMLElement {
  constructor() { super(); this.attachShadow({ mode:"open" }); this.generation = 0; }
  configure(hass, info) {
    this._hass = hass;
    const entries = hass?.user?.is_admin ? info?.providers?.ring?.entries || [] : [];
    const key = JSON.stringify(entries.map(e => e.entry_id));
    if (key === this.key) return;
    this.key = key; this.load(entries);
  }
  async load(entries) {
    const generation = ++this.generation;
    this.live?.close(); this.hidden = true;
    const results = await Promise.allSettled(entries.map(async entry => {
      const result = await this._hass.callWS({ type:"media_bridge/ring/cameras", entry_id:entry.entry_id });
      return result.cameras.map(camera => ({ ...camera, entry_id:entry.entry_id }));
    }));
    if (generation !== this.generation) return;
    this.cameras = results.flatMap(r => r.status === "fulfilled" ? r.value : []);
    const seen = new Set();
    this.cameras = this.cameras.filter(c => !seen.has(c.device_id) && seen.add(c.device_id));
    this.dispatchEvent(new CustomEvent("ring-cameras-loaded", { detail:{ count:this.cameras.length }, bubbles:true, composed:true }));
    if (!this.cameras.length && !results.some(r => r.status === "rejected")) return;
    this.hidden = false;
    this.shadowRoot.innerHTML = `<style>
      :host { display:block;margin:16px 0; } :host([hidden]) { display:none; }
      section { padding:16px;border:1px solid var(--divider-color);border-radius:20px; }
      button,select { min-height:44px;font:inherit;color:var(--primary-text-color);background:var(--card-background-color);border:1px solid var(--divider-color);border-radius:12px;padding:8px; }
      select { max-width:100%; } .actions { display:flex;align-items:center;gap:12px;flex-wrap:wrap; }
      button { min-width:44px;display:inline-flex;align-items:center;justify-content:center;gap:8px;cursor:pointer; }
    </style><section><h2></h2><p id="notice" role="status"></p><div class="actions"><select></select>
      <button id="live"><ha-icon icon="mdi:video-wireless-outline"></ha-icon><span></span></button>
      <button id="reload"><ha-icon icon="mdi:refresh"></ha-icon></button></div><p id="location"></p></section>`;
    const root = this.shadowRoot;
    root.querySelector("h2").textContent = copy(this, "Telecamere Ring");
    root.querySelector("#notice").textContent = copy(this, results.some(r => r.status === "rejected")
      ? "Inventario telecamere Ring non disponibile. Riprova."
      : "Supporto sperimentale: live e audio da verificare sul tuo modello Ring. Massimo 2 minuti per sessione.");
    const select = root.querySelector("select");
    select.setAttribute("aria-label", copy(this, "Telecamere Ring"));
    select.replaceChildren(...this.cameras.map((camera, index) => {
      const option = document.createElement("option"); option.value = String(index); option.textContent = camera.name; return option;
    }));
    select.hidden = !this.cameras.length;
    select.onchange = () => { this.live?.close(); root.querySelector("#location").textContent = this.cameras[select.value]?.location_name || ""; };
    select.onchange();
    const live = root.querySelector("#live"); live.disabled = !this.cameras.length;
    live.querySelector("span").textContent = copy(this, "Apri live");
    live.onclick = () => { this.live ||= new RingCameraDialog(this); this.live.open(this._hass, this.cameras[select.value]); };
    const reload = root.querySelector("#reload"); reload.title = copy(this, "Aggiorna elenco telecamere");
    reload.setAttribute("aria-label", reload.title); reload.onclick = () => this.load(entries);
  }
  disconnectedCallback() { ++this.generation; this.key = null; this.live?.close(); }
}
customElements.define("vistoda-ring-camera-gallery", RingCameraGallery);
