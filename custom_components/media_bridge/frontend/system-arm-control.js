import { copy, localizeCopy } from "./panel-copy.js";
import { BASE_STYLES } from "./panel-styles.js";

// Shared, observed-state control. Never optimistically label a system armed.
class SystemArmControl extends HTMLElement {
  constructor() {
    super(); this.attachShadow({ mode: "open" });
    this.shadowRoot.innerHTML = `<style>${BASE_STYLES}
      .system-row { display:flex; justify-content:space-between; align-items:center; gap:12px; flex-wrap:wrap; }
      #status { margin-top:6px; } #name { overflow-wrap:anywhere; }
    </style><div class="system-row"><div><strong id="name"></strong><div class="muted" id="state"></div></div>
      <button id="toggle"><ha-icon></ha-icon><span></span></button></div><div id="status" role="status" class="muted"></div>`;
    this.$ = (id) => this.shadowRoot.getElementById(id);
    this.$("toggle").addEventListener("click", () => this.toggle());
  }
  configure(hass, entityId, name) {
    if (entityId !== this.entityId) this.clearPending();
    this._hass = hass; this.entityId = entityId; this.name = name; this.render();
  }
  render() {
    localizeCopy(this.shadowRoot, this);
    const state = this._hass?.states?.[this.entityId];
    const armed = state?.state?.startsWith("armed_") || state?.state === "triggered";
    const known = armed || state?.state === "disarmed";
    this.$("name").textContent = this.name || "";
    this.$("state").textContent = copy(this, armed ? "Armato" : known ? "Disarmato" : "Stato non disponibile");
    const button = this.$("toggle");
    button.querySelector("span").textContent = copy(this, armed ? "Disarma" : "Arma");
    button.querySelector("ha-icon").setAttribute("icon", armed ? "mdi:shield-off-outline" : "mdi:shield-lock-outline");
    button.title = button.querySelector("span").textContent;
    button.disabled = !known || Boolean(this.pending) || !this.entityId;
    if (state?.attributes?.code_format) button.disabled = true;
    if (!armed && !(Number(state?.attributes?.supported_features) & 2)) button.disabled = true;
    if (this.pending?.accepted && state?.state === this.pending.expected) {
      const message = copy(this, armed ? "Sistema armato" : "Sistema disarmato");
      this.clearPending(); this.$("status").textContent = message;
      this.dispatchEvent(new CustomEvent("hass-notification", { bubbles: true, composed: true, detail: { message } }));
      button.disabled = false;
    }
  }
  async toggle() {
    if (this.$("toggle").disabled || this.pending) return;
    const state = this._hass.states[this.entityId];
    const arm = state.state === "disarmed";
    const pending = { expected: arm ? "armed_away" : "disarmed", accepted: false };
    this.pending = pending; this.$("status").textContent = copy(this, "Operazione in corso…"); this.render();
    this.timeout = setTimeout(() => {
      if (this.pending !== pending) return;
      this.clearPending(); this.$("status").textContent = copy(this, "Stato non confermato. Verifica il sistema prima di riprovare."); this.render();
    }, 20000);
    try {
      await this._hass.callService("alarm_control_panel", arm ? "alarm_arm_away" : "alarm_disarm", { entity_id: this.entityId });
      if (this.pending !== pending) return;
      pending.accepted = true; this.render();
    } catch {
      if (this.pending !== pending) return;
      this.clearPending(); this.$("status").textContent = copy(this, "Operazione non riuscita"); this.render();
    }
  }
  clearPending() { clearTimeout(this.timeout); this.pending = null; }
  disconnectedCallback() { this.clearPending(); }
}
if (!customElements.get("vistoda-system-arm-control")) customElements.define("vistoda-system-arm-control", SystemArmControl);
