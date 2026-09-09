import { BASE_STYLES } from "./panel-styles.js";
import { booleanStateText, videoQualityOptions } from "./blink-setting-model.js";
import { BLINK_SETTING_STYLES } from "./blink-setting-styles.js";

const META = {
  motion_detection: ["Rilevamento movimento", "Abilita gli eventi di movimento", "Movimento"],
  motion_sensitivity: ["Sensibilità", "Sensibilità del sensore di movimento", "Movimento"],
  retrigger_time: ["Tempo di riattivazione", "Pausa tra due eventi", "Movimento", "s"],
  early_notification: ["Notifica anticipata", "Avvisa all’inizio del movimento", "Movimento"],
  video_recording: ["Registrazione video", "Consenti alla camera di registrare", "Video e audio"],
  audio_streaming: ["Streaming audio", "Consenti le funzioni audio", "Video e audio"],
  clip_length: ["Durata clip", "Durata delle clip di movimento", "Video e audio", "s"],
  video_quality: ["Qualità video", "Regola la risoluzione video della telecamera", "Video e audio"],
  end_clip_early: ["Termina clip a movimento finito", "Ferma la clip quando cessa il movimento", "Video e audio"],
  night_vision: ["Visione notturna", "Modalità degli infrarossi", "Visione notturna"],
  ir_intensity: ["Intensità IR", "Luminosità dei LED infrarossi", "Visione notturna"],
  flip_video: ["Ruota video", "Ruota l’immagine quando la camera è capovolta", "Video e foto"],
  photo_capture: ["Acquisizione foto", "Una foto ogni ora; richiede un piano Blink idoneo", "Video e foto"],
  auto_thumbnail: ["Miniatura automatica", "Aggiorna la miniatura durante gli eventi", "Video e foto"],
  status_led: ["LED di stato", "Quando deve accendersi il LED della telecamera", "Generali"],
  speaker_volume: ["Volume altoparlante", "Livello audio dell’altoparlante della telecamera", "Audio"],
  sync_strength: ["Segnale Sync Module", "Ultima intensità radio rilevata", "Diagnostica", "dBm"],
  camera_name: ["Nome telecamera", "Nome mostrato da Blink e Vistoda", "Generali"],
  temperature_alerts: ["Avvisi temperatura", "Stato configurato nell’account Blink", "Diagnostica"],
  temperature_min: ["Temperatura minima", "Soglia inferiore", "Diagnostica", "°F"],
  temperature_max: ["Temperatura massima", "Soglia superiore", "Diagnostica", "°F"],
};

const OPTION_LABELS = {
  off: "Disattivata", on: "Attivata", auto: "Automatica",
  saver: "Risparmio", standard: "Standard", best: "Migliore",
  low: "Bassa", medium: "Media", high: "Alta", recording: "Durante la registrazione",
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
      <style>${BASE_STYLES}${BLINK_SETTING_STYLES}</style>
      <section class="card settings"><header><div><div class="eyebrow">Dettaglio camera</div>
        <h3 id="title">Impostazioni Blink</h3><div class="muted">Valori letti direttamente
        dalla camera, senza esporre credenziali.</div></div><button id="reload"
        aria-label="Ricarica impostazioni">↻</button></header>
        <div id="summary"></div><div id="fields"></div>
        <div class="muted" id="status" role="status"></div>
        <div class="notice muted">Vistoda mostra soltanto funzioni riconosciute per questo
        modello. Audio bidirezionale Blink e rimozione rimangono nascosti finché
        i relativi contratti non superano le verifiche di sicurezza.</div></section>`;
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
    this.$("title").textContent = this._settings?.name || this._camera.name || "Impostazioni Blink";
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
    const row = document.createElement("div");
    row.className = `field${field.key === "video_quality" ? " quality" : ""}`;
    const text = document.createElement("div");
    const label = document.createElement("strong"); label.textContent = meta[0]; text.append(label);
    const help = document.createElement("small"); help.textContent = meta[1]; text.append(help);
    const control = document.createElement("div"); control.className = "control";
    control.append(this._control(field, meta)); row.append(text, control); return row;
  }

  _control(field, meta) {
    const [label, , , unit = ""] = meta;
    const editable = field.writable && this._hass?.user?.is_admin === true;
    if (field.key === "video_quality") return this._qualityControl(field, editable, label);
    if (!editable) {
      const value = document.createElement("span"); value.className = "readonly";
      value.textContent = this._value(field.value, unit); return value;
    }
    if (field.kind === "text") return this._textControl(field, label);
    if (field.kind === "boolean") {
      const button = document.createElement("button"); button.className = "toggle";
      button.setAttribute("role", "switch"); button.setAttribute("aria-checked", String(field.value));
      button.setAttribute("aria-label", `${label}: ${booleanStateText(field.value)}`);
      const state = document.createElement("span"); state.className = "toggle-state";
      state.textContent = booleanStateText(field.value);
      const track = document.createElement("span"); track.className = "switch-track";
      track.setAttribute("aria-hidden", "true"); button.append(state, track);
      button.addEventListener("click", () => this._update(field, !field.value)); return button;
    }
    if (field.kind === "select") {
      const select = document.createElement("select"); select.setAttribute("aria-label", label);
      for (const option of field.options) select.add(new Option(OPTION_LABELS[option] || option, option));
      select.value = field.value; select.addEventListener("change", () => this._update(field, select.value));
      return select;
    }
    const wrapper = document.createElement("label");
    const input = document.createElement("input"); input.type = "range";
    input.setAttribute("aria-label", label);
    Object.assign(input, { min: field.min, max: field.max, step: field.step, value: field.value });
    const output = document.createElement("span"); output.className = "value";
    output.textContent = this._value(field.value, unit);
    input.addEventListener("input", () => { output.textContent = this._value(Number(input.value), unit); });
    input.addEventListener("change", () => this._update(field, Number(input.value)));
    wrapper.append(input, output); return wrapper;
  }

  _textControl(field, label) {
    const wrapper = document.createElement("div"); wrapper.className = "text-control";
    const input = document.createElement("input"); input.type = "text";
    input.value = field.value; input.maxLength = field.max || 255;
    input.setAttribute("aria-label", label);
    const save = document.createElement("button"); save.textContent = "Salva"; save.disabled = true;
    input.addEventListener("input", () => { save.disabled = input.value.trim() === field.value; });
    save.addEventListener("click", () => this._update(field, input.value));
    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !save.disabled) { event.preventDefault(); save.click(); }
    });
    wrapper.append(input, save); return wrapper;
  }

  _qualityControl(field, editable, label) {
    const group = document.createElement("fieldset"); group.className = "quality-options";
    group.setAttribute("aria-label", label);
    const name = `video-quality-${this._camera?.alias || "camera"}`;
    for (const option of videoQualityOptions(field.options, field.value)) {
      const row = document.createElement("label"); row.className = "quality-option";
      const input = document.createElement("input"); input.type = "radio";
      input.name = name; input.value = option.value; input.checked = option.value === field.value;
      input.disabled = !editable;
      input.addEventListener("change", () => { if (input.checked) this._update(field, option.value); });
      const copy = document.createElement("span");
      const title = document.createElement("strong"); title.textContent = option.label;
      const help = document.createElement("small"); help.textContent = option.description;
      copy.append(title, help); row.append(input, copy); group.append(row);
    }
    return group;
  }

  _value(value, unit) {
    if (typeof value === "boolean") return booleanStateText(value);
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
