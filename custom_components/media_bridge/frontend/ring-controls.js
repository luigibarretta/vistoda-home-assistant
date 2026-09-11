import { copy, localizeCopy } from "./panel-copy.js";
import { BASE_STYLES } from "./panel-styles.js";

class RingControls extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._mounted = false;
    this._controls = {};
    this._doorBusy = false;
    this._doorReset = null;
  }

  set hass(value) {
    this._hass = value;
    if (this._mounted) this._refresh();
  }

  configure(controls, entry) {
    this._controls = controls || {};
    this._entry = entry;
    if (!this._mounted) this._mount();
    this._refresh();
  }

  _mount() {
    this._mounted = true;
    this.shadowRoot.innerHTML = `
      <style>${BASE_STYLES}
        :host{display:block;margin-top:16px}.card{padding:22px;border-radius:22px;
          background:var(--card-background-color);box-shadow:var(--ha-card-box-shadow);
          border:1px solid var(--divider-color)}h2{margin:0 0 4px;font-size:19px}
        .hint{color:var(--secondary-text-color);font-size:14px;line-height:1.45}
        .door{display:flex;justify-content:space-between;align-items:center;gap:18px;
          padding-bottom:18px;border-bottom:1px solid var(--divider-color)}
        button{min-height:40px;border:0;border-radius:12px;padding:8px 13px;cursor:pointer;
          color:white;background:linear-gradient(135deg,#16835e,#28a579);font:inherit;font-weight:700;
          display:inline-flex;align-items:center;gap:7px;white-space:nowrap}
        button ha-icon{--mdc-icon-size:20px}
        button:disabled{opacity:.48;cursor:not-allowed}.levels{display:grid;gap:16px;margin-top:18px}
        label{display:grid;grid-template-columns:150px 1fr 32px;align-items:center;gap:12px}
        output{text-align:right;font-variant-numeric:tabular-nums}input{width:100%;accent-color:var(--primary-color)}
        .policy{display:flex;justify-content:space-between;align-items:center;gap:16px;margin-bottom:17px;
          padding-bottom:17px;border-bottom:1px solid var(--divider-color)}.policy input{width:22px;height:22px}
        .feedback{min-height:18px;margin-top:13px;color:var(--secondary-text-color);font-size:13px}
        .battery{display:inline-flex;align-items:center;gap:6px;margin-top:7px;font-weight:650}
        .battery ha-icon{--mdc-icon-size:19px}
        @media(max-width:520px){.card{padding:18px}.door{align-items:start;flex-direction:column}
          label{grid-template-columns:1fr 34px}label span{grid-column:1/-1}}
      </style>
      <section class="card">
        <label class="policy"><span><strong><span data-copy="Delega a Ring ufficiale">Delega a Ring ufficiale</span></strong><br>
          <span class="hint" id="policy-hint"><span data-copy="Verifica integrazione…">Verifica integrazione…</span></span></span>
          <input id="delegate_controls" type="checkbox" disabled></label>
        <div class="door"><div><h2><span data-copy="Portone e volumi">Portone e volumi</span></h2>
          <div class="hint" id="control-source"><span data-copy="Sorgente controlli in verifica">Sorgente controlli in verifica</span></div>
          <div class="battery"><ha-icon icon="mdi:battery"></ha-icon>
            <span id="battery"><span data-copy="Batteria —">Batteria —</span></span></div></div>
          <button id="door"><ha-icon id="door-icon" icon="mdi:lock"></ha-icon>
            <span id="door-label"><span data-copy="Apri portone">Apri portone</span></span></button></div>
        <div class="levels">
          ${this._slider("doorbell_volume", "Suoneria citofono")}
          ${this._slider("mic_volume", "Microfono citofono")}
          ${this._slider("voice_volume", "Voce citofono")}
        </div><div class="feedback" id="feedback"></div>
      </section>`; localizeCopy(this.shadowRoot, this);
    this.$ = (id) => this.shadowRoot.getElementById(id);
    this.$("delegate_controls").addEventListener("change", () => this._setDelegation());
    this.$("door").addEventListener("click", () => this._openDoor());
    for (const key of ["doorbell_volume", "mic_volume", "voice_volume"]) {
      const slider = this.$(key);
      slider.addEventListener("input", () => { this.$(`${key}-value`).value = slider.value; });
      slider.addEventListener("change", () => this._setVolume(key, slider.value));
    }
  }

  _slider(key, label) {
    return `<label><span data-copy="${label}">${label}</span><input id="${key}" type="range" disabled>
      <output id="${key}-value">—</output></label>`;
  }

  _refresh() {
    if (!this._hass || !this._mounted) return;
    localizeCopy(this.shadowRoot, this);
    const delegation = this._state("delegate_controls");
    const delegateToggle = this.$("delegate_controls");
    const officialAvailable = delegation && delegation.state !== "unavailable";
    delegateToggle.disabled = !officialAvailable;
    delegateToggle.checked = delegation?.state === "on";
    this.$("policy-hint").textContent = officialAvailable
      ? copy(this, "Puoi passare istantaneamente tra Vistoda nativo e Ring ufficiale")
      : copy(this, "Ring ufficiale non rilevato · Vistoda nativo obbligatorio");
    this.$("control-source").textContent = delegateToggle.checked
      ? copy(this, "Sorgente: integrazione Ring ufficiale")
      : copy(this, "Gestito da Vistoda");
    const battery = this._state("battery");
    this.$("battery").textContent = battery && !["unknown", "unavailable"].includes(battery.state)
      ? copy(this, "Batteria {p0}%", { p0: battery.state }) : copy(this, "Batteria non disponibile");
    this.$("door").disabled = this._doorBusy || !this._usable("open_door");
    for (const key of ["doorbell_volume", "mic_volume", "voice_volume"]) {
      const state = this._state(key);
      const slider = this.$(key);
      slider.disabled = !state || ["unknown", "unavailable"].includes(state.state);
      if (slider.disabled) { this.$(`${key}-value`).value = "—"; continue; }
      slider.min = state.attributes.min ?? 0;
      slider.max = state.attributes.max ?? 100;
      slider.step = state.attributes.step ?? 1;
      if (!slider.matches(":active")) slider.value = state.state;
      this.$(`${key}-value`).value = slider.value;
    }
  }

  _state(key) { return this._hass?.states?.[this._controls[key]]; }

  _usable(key) {
    const state = this._state(key);
    return state && state.state !== "unavailable";
  }

  async _openDoor() {
    if (this._doorBusy || !this._usable("open_door")) return;
    const identity = [this._entry?.device_name || this._entry?.name,
      this._entry?.location_name, this._entry?.city].filter(Boolean).join(" · ");
    if (!window.confirm(copy(this, "Aprire l’ingresso {p0}?", { p0: identity || "Ring Intercom" }))) return;
    clearTimeout(this._doorReset);
    this._doorBusy = true;
    this._setDoorVisual("sending");
    try {
      await this._hass.callService("button", "press", { entity_id: this._controls.open_door });
      this.$("feedback").textContent = copy(this, "Comando di apertura inviato.");
      this._setDoorVisual("sent");
    } catch (_error) {
      this.$("feedback").textContent = copy(this, "Apertura non riuscita: controlla l’integrazione Ring.");
      this._setDoorVisual("error");
    }
    this._doorReset = setTimeout(() => {
      this._doorBusy = false;
      this._setDoorVisual("ready");
      this._refresh();
    }, 1800);
  }

  _setDoorVisual(state) {
    const visuals = {
      ready: ["mdi:lock", copy(this, "Apri portone")],
      sending: ["mdi:lock-open-variant", copy(this, "Invio…")],
      sent: ["mdi:lock-open-variant", copy(this, "Comando inviato")],
      error: ["mdi:lock-alert", copy(this, "Non riuscito")],
    };
    const [icon, label] = visuals[state];
    this.$("door-icon").setAttribute("icon", icon);
    this.$("door-label").textContent = label;
    this.$("door").disabled = state !== "ready" || !this._usable("open_door");
  }

  async _setDelegation() {
    const enabled = this.$("delegate_controls").checked;
    try {
      await this._hass.callService("switch", enabled ? "turn_on" : "turn_off", {
        entity_id: this._controls.delegate_controls,
      });
      this.$("feedback").textContent = enabled
        ? copy(this, "Controlli delegati a Ring ufficiale.")
        : copy(this, "Controlli affidati al bridge Vistoda nativo.");
    } catch (_error) {
      this.$("feedback").textContent = copy(this, "Cambio sorgente non riuscito.");
      this._refresh();
    }
  }

  async _setVolume(key, value) {
    try {
      await this._hass.callService("number", "set_value", {
        entity_id: this._controls[key], value: Number(value),
      });
      this.$("feedback").textContent = copy(this, "Volume aggiornato.");
    } catch (_error) {
      this.$("feedback").textContent = copy(this, "Aggiornamento volume non riuscito.");
      this._refresh();
    }
  }

  disconnectedCallback() { clearTimeout(this._doorReset); }
}

if (!customElements.get("vistoda-ring-controls")) {
  customElements.define("vistoda-ring-controls", RingControls);
}
