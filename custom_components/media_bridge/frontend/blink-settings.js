import { BASE_STYLES } from "./panel-styles.js";

const META = {
  motion_detection: ["Rilevamento movimento", "Abilita gli eventi di movimento", "Movimento"],
  motion_sensitivity: ["Sensibilità", "Sensibilità del sensore di movimento", "Movimento"],
  retrigger_time: ["Tempo di riattivazione", "Pausa tra due eventi", "Movimento", "s"],
  early_notification: ["Notifica anticipata", "Avvisa all’inizio del movimento", "Movimento"],
  video_recording: ["Registrazione video", "Consenti alla camera di registrare", "Video e audio"],
  audio_streaming: ["Streaming audio", "Consenti le funzioni audio", "Video e audio"],
  clip_length: ["Durata clip", "Durata delle clip di movimento", "Video e audio", "s"],
  video_quality: ["Qualità video", "Risoluzione usata dalla camera", "Video e audio"],
  end_clip_early: ["Termina clip a movimento finito", "Ferma la clip quando cessa il movimento", "Video e audio"],
  night_vision: ["Visione notturna", "Modalità degli infrarossi", "Visione notturna"],
  ir_intensity: ["Intensità IR", "Luminosità dei LED infrarossi", "Visione notturna"],
  temperature_alerts: ["Avvisi temperatura", "Stato configurato nell’account Blink", "Diagnostica"],
  temperature_min: ["Temperatura minima", "Soglia inferiore", "Diagnostica", "°F"],
  temperature_max: ["Temperatura massima", "Soglia superiore", "Diagnostica", "°F"],
};

const OPTION_LABELS = {
  off: "Disattivata", on: "Attivata", auto: "Automatica",
  saver: "Risparmio", standard: "Standard", best: "Massima",
};

class VistodaBlinkSettings extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._request = 0;
    this._mount();
  }

  set hass(value) { this._hass = value; }
  set camera(value) {
    const alias = value?.alias || "";
    if (alias === this._camera?.alias) return;
    this._camera = value;
    this._settings = null;
    this._render();
    if (alias) this._load();
  }

  _mount() {
    this.shadowRoot.innerHTML = `
      <style>${BASE_STYLES}
        :host { display:block; margin-top:18px; }
        .settings { padding:20px; }
        header { display:flex; justify-content:space-between; align-items:flex-start; gap:14px; }
        h3 { margin:3px 0 4px; font-size:21px; }
        #summary { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:8px;
          margin:16px 0; }
        .datum { padding:11px; border-radius:12px; background:var(--secondary-background-color); }
        .datum span { display:block; color:var(--secondary-text-color); font-size:12px; }
        .datum strong { display:block; margin-top:3px; overflow-wrap:anywhere; }
        .section-title { margin:20px 0 7px; font-size:13px; color:var(--secondary-text-color);
          letter-spacing:.05em; text-transform:uppercase; }
        .field { display:flex; align-items:center; justify-content:space-between; gap:18px;
          min-height:68px; padding:12px 0; border-top:1px solid var(--divider-color); }
        .field:first-child { border-top:0; } .field strong { display:block; }
        .field small { display:block; margin-top:3px; color:var(--secondary-text-color); }
        .control { flex:0 0 auto; min-width:112px; text-align:right; }
        .toggle { min-width:58px; border-radius:999px; padding:7px; background:var(--divider-color); }
        .toggle[aria-checked="true"] { color:#fff; background:var(--primary-color); }
        select, input { min-height:42px; max-width:150px; border:1px solid var(--divider-color);
          border-radius:10px; padding:7px; color:var(--primary-text-color);
          background:var(--secondary-background-color); font:inherit; }
        input[type="range"] { min-height:30px; width:145px; padding:0; }
        .value { display:block; margin-top:3px; font-size:13px; }
        .readonly { color:var(--secondary-text-color); }
        #status { min-height:21px; margin-top:12px; }
        .notice { margin-top:16px; padding:12px; border-radius:12px;
          background:color-mix(in srgb,var(--primary-color) 10%,transparent); }
        @media (max-width:650px) {
          #summary { grid-template-columns:repeat(2,minmax(0,1fr)); }
          .settings { padding:16px; } .field { align-items:flex-start; }
          .control { min-width:96px; } input[type="range"] { width:115px; }
        }
      </style>
      <section class="card settings"><header><div><div class="eyebrow">Dettaglio camera</div>
        <h3 id="title">Impostazioni Blink</h3><div class="muted">Valori letti direttamente
        dalla camera, senza esporre credenziali.</div></div><button id="reload"
        aria-label="Ricarica impostazioni">↻</button></header>
        <div id="summary"></div><div id="fields"></div>
        <div class="muted" id="status" role="status"></div>
        <div class="notice muted">Vistoda mostra soltanto funzioni riconosciute per questo
        modello. Zone, rinomina, LED e rimozione restano nell’app Blink finché i relativi
        contratti non superano le verifiche di sicurezza.</div></section>`;
    this.$ = (id) => this.shadowRoot.getElementById(id);
    this.$("reload").addEventListener("click", () => this._load());
  }

  async _load() {
    if (!this._hass || !this._camera?.alias) return;
    const request = ++this._request;
    this.$("status").textContent = "Lettura impostazioni…";
    this.$("reload").disabled = true;
    try {
      const result = await this._hass.callWS({
        type: "blink_live_bridge/camera/settings", alias: this._camera.alias,
      });
      if (request === this._request) { this._settings = result; this._render(); }
    } catch (_error) {
      if (request === this._request) this.$("status").textContent =
        "Impostazioni avanzate non disponibili per questo modello.";
    } finally {
      if (request === this._request) this.$("reload").disabled = false;
    }
  }

  _render() {
    this.hidden = !this._camera?.alias;
    if (this.hidden) return;
    this.$("title").textContent = this._camera.name || "Impostazioni Blink";
    if (!this._settings) { this.$("summary").replaceChildren(); this.$("fields").replaceChildren(); return; }
    this._renderSummary();
    const groups = new Map();
    for (const field of this._settings.settings || []) {
      const section = (META[field.key] || [field.key, "", "Altro"])[2];
      if (!groups.has(section)) groups.set(section, []);
      groups.get(section).push(field);
    }
    const content = [];
    for (const [section, fields] of groups) {
      const title = document.createElement("h4"); title.className = "section-title";
      title.textContent = section; content.push(title);
      const list = document.createElement("div");
      list.replaceChildren(...fields.map((field) => this._field(field))); content.push(list);
    }
    this.$("fields").replaceChildren(...content);
    this.$("status").textContent = groups.size ? "" : "Nessuna impostazione riconosciuta.";
  }

  _renderSummary() {
    const data = this._settings;
    const temp = Number.isFinite(data.temperature_f)
      ? `${((data.temperature_f - 32) * 5 / 9).toLocaleString("it-IT", { maximumFractionDigits: 1 })} °C` : "—";
    const values = [["Modello", data.product_type || data.camera_type], ["Firmware", data.firmware],
      ["Segnale Wi-Fi", Number.isFinite(data.wifi_dbm) ? `${data.wifi_dbm} dBm` : null],
      ["Temperatura", temp]];
    this.$("summary").replaceChildren(...values.map(([label, value]) => {
      const item = document.createElement("div"); item.className = "datum";
      const caption = document.createElement("span"); caption.textContent = label;
      const content = document.createElement("strong"); content.textContent = value || "—";
      item.append(caption, content); return item;
    }));
  }

  _field(field) {
    const meta = META[field.key] || [field.key, "", "Altro"];
    const row = document.createElement("div"); row.className = "field";
    const text = document.createElement("div");
    const label = document.createElement("strong"); label.textContent = meta[0]; text.append(label);
    const help = document.createElement("small"); help.textContent = meta[1]; text.append(help);
    const control = document.createElement("div"); control.className = "control";
    control.append(this._control(field, meta[3])); row.append(text, control); return row;
  }

  _control(field, unit = "") {
    const admin = this._hass?.user?.is_admin !== false;
    if (!field.writable || !admin) {
      const value = document.createElement("span"); value.className = "readonly";
      value.textContent = this._value(field.value, unit); return value;
    }
    if (field.kind === "boolean") {
      const button = document.createElement("button"); button.className = "toggle";
      button.setAttribute("role", "switch"); button.setAttribute("aria-checked", String(field.value));
      button.textContent = field.value ? "Attiva" : "Spenta";
      button.addEventListener("click", () => this._update(field, !field.value)); return button;
    }
    if (field.kind === "select") {
      const select = document.createElement("select");
      for (const option of field.options) select.add(new Option(OPTION_LABELS[option] || option, option));
      select.value = field.value; select.addEventListener("change", () => this._update(field, select.value));
      return select;
    }
    const wrapper = document.createElement("label");
    const input = document.createElement("input"); input.type = "range";
    Object.assign(input, { min: field.min, max: field.max, step: field.step, value: field.value });
    const output = document.createElement("span"); output.className = "value";
    output.textContent = this._value(field.value, unit);
    input.addEventListener("input", () => { output.textContent = this._value(Number(input.value), unit); });
    input.addEventListener("change", () => this._update(field, Number(input.value)));
    wrapper.append(input, output); return wrapper;
  }

  _value(value, unit) {
    if (typeof value === "boolean") return value ? "Attiva" : "Spenta";
    return `${OPTION_LABELS[value] || value}${unit ? ` ${unit}` : ""}`;
  }

  async _update(field, value) {
    if (["video_recording", "audio_streaming"].includes(field.key)
      && !globalThis.confirm(`Confermi la modifica di “${META[field.key][0]}”?`)) { this._render(); return; }
    this.$("status").textContent = "Salvataggio e verifica…";
    try {
      this._settings = await this._hass.callWS({ type: "blink_live_bridge/camera/settings/update",
        alias: this._camera.alias, key: field.key, value, revision: this._settings.revision });
      this._render(); this.$("status").textContent = "Impostazione verificata sulla camera.";
    } catch (_error) {
      this.$("status").textContent = "Modifica non confermata: il valore precedente è stato preservato.";
      await this._load();
    }
  }
}

if (!customElements.get("vistoda-blink-settings")) {
  customElements.define("vistoda-blink-settings", VistodaBlinkSettings);
}
