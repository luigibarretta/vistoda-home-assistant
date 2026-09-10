import { BASE_STYLES } from "./panel-styles.js";
import "./ring-identity-dialog.js";

class RingDeviceIdentity extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._mounted = false;
    this._busy = false;
  }

  configure(hass, entry) {
    this._hass = hass;
    this._entry = entry;
    if (!this._mounted) this._mount();
    this.$("dialog").configure(hass, entry, entry.identity_configuration);
    this._render();
  }

  setBusy(value) {
    this._busy = Boolean(value);
    if (this._mounted) this.$("edit").disabled = this._busy || !this._entry?.identity_configuration;
  }

  _mount() {
    this._mounted = true;
    this.shadowRoot.innerHTML = `
      <style>${BASE_STYLES}
        :host{display:block;min-width:0}.title{display:flex;align-items:start;gap:10px}
        .copy{min-width:0;flex:1}h2{margin:4px 0 7px;font-size:22px;overflow-wrap:anywhere}
        .edit{min-width:44px;min-height:44px;padding:8px}.summary{display:flex;align-items:center;gap:7px;
          margin-top:9px;color:var(--secondary-text-color);font-size:13px}.summary ha-icon{
          --mdc-icon-size:18px;color:var(--primary-color)}
      </style><div class="title"><div class="copy"><div class="eyebrow">Ring Intercom</div>
        <h2 id="name">Citofono</h2></div><button class="edit" id="edit" disabled
        aria-label="Modifica identità del dispositivo Ring" title="Modifica identità Ring"
        data-tooltip="Scegli i nomi del dispositivo e della casa usati nelle notifiche">
        <ha-icon icon="mdi:account-edit-outline"></ha-icon></button></div>
        <div class="muted">Ascolto e conversazione simultanei · massimo 2 minuti</div>
        <div class="summary"><ha-icon icon="mdi:home-map-marker"></ha-icon>
          <span id="location">Location Ring</span></div>
        <vistoda-ring-identity-dialog id="dialog"></vistoda-ring-identity-dialog>`;
    this.$ = (id) => this.shadowRoot.getElementById(id);
    this.$("edit").addEventListener("click", () => this.$("dialog").show());
    this.$("dialog").addEventListener("identity-updated", (event) => {
      Object.assign(this._entry, event.detail.identity, {
        identity_configuration: event.detail.identity_configuration,
      });
      this.$("dialog").configure(this._hass, this._entry, event.detail.identity_configuration);
      this._render();
      this.dispatchEvent(new CustomEvent("identity-updated", { bubbles: true, composed: true }));
    });
  }

  _render() {
    this.$("name").textContent = this._entry.device_name
      || this._entry.name.replace(/^Vistoda · /, "");
    const location = this._entry.location_name || "Location Ring";
    const city = this._entry.city || "";
    this.$("location").textContent = city && !location.toLocaleLowerCase("it-IT")
      .endsWith(` in ${city}`.toLocaleLowerCase("it-IT")) ? `${location} · ${city}` : location;
    this.setBusy(this._busy);
  }
}

if (!customElements.get("vistoda-ring-device-identity")) {
  customElements.define("vistoda-ring-device-identity", RingDeviceIdentity);
}
