import { BASE_STYLES } from "./panel-styles.js";
import {
  booleanStateText, temperatureValueText, videoQualityOptions,
} from "./blink-setting-model.js";
import { BLINK_SETTING_STYLES } from "./blink-setting-styles.js";
import {
  BLINK_OPTION_LABELS, BLINK_SETTING_META, BLINK_SETTING_SECTIONS, settingSection,
} from "./blink-setting-schema.js";
import {
  cameraDraft, commitDraft, reconcileDraft, stagedField, stageValue,
} from "./blink-setting-draft.js";

class VistodaBlinkSettings extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._request = 0; this._drafts = new Map();
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
    const sections = BLINK_SETTING_SECTIONS.map((section, index) => `
      <details class="setting-section" data-section="${section.key}" ${index === 0 ? "open" : ""}>
        <summary><ha-icon icon="${section.icon}"></ha-icon><span class="section-copy">
          <strong>${section.title}</strong><small>${section.description}</small></span>
          <ha-icon class="chevron" icon="mdi:chevron-down"></ha-icon></summary>
        <div class="section-body">${section.key === "general" ? '<div id="summary"></div>' : ""}
          <div id="group-${section.key}"></div>${section.key === "privacy" ? '<slot name="zones"></slot>' : ""}</div>
      </details>`).join("");
    this.shadowRoot.innerHTML = `
      <style>${BASE_STYLES}${BLINK_SETTING_STYLES}</style>
      <section class="card settings"><header><div><div class="eyebrow">Dettaglio camera</div>
        <h3 id="title">Impostazioni Blink</h3><div class="muted">Valori letti direttamente
        dalla camera, senza esporre credenziali.</div></div><button id="reload"
        aria-label="Rileggi le impostazioni dal cloud Blink"
        title="Rileggi le impostazioni dal cloud Blink"
        data-tooltip="Rilegge dal cloud Blink le impostazioni e conserva le modifiche non salvate">↻</button></header>
        <div class="accordion" id="fields">${sections}</div><div class="draft-actions" id="draft-actions"
          hidden><span class="muted" id="draft-count"></span><button id="discard">Annulla</button>
          <button class="primary" id="save">Salva modifiche</button></div>
        <div class="muted" id="status" role="status"></div>
        <div class="notice muted">Vistoda mostra soltanto funzioni riconosciute per questo
        modello. Audio bidirezionale Blink e rimozione rimangono nascosti finché
        i relativi contratti non superano le verifiche di sicurezza.</div></section>`;
    this.$ = (id) => this.shadowRoot.getElementById(id);
    this.$("reload").addEventListener("click", () => this._load());
    this.$("discard").addEventListener("click", () => this._discard());
    this.$("save").addEventListener("click", () => this._saveDraft());
    for (const section of this.shadowRoot.querySelectorAll("details")) {
      section.addEventListener("toggle", () => this._keepSingleSectionOpen(section));
    }
  }

  _keepSingleSectionOpen(active) {
    if (!active.open) return;
    for (const section of this.shadowRoot.querySelectorAll("details")) {
      if (section !== active) section.open = false;
    }
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
      if (request === this._request) { this._settings = result;
        reconcileDraft(result, this._draft()); this._render(); }
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
    if (!this._settings) { this.$("summary").replaceChildren();
      for (const section of BLINK_SETTING_SECTIONS) this.$(`group-${section.key}`).replaceChildren();
      return; }
    this._renderSummary();
    const groups = new Map(BLINK_SETTING_SECTIONS.map((section) => [section.key, []]));
    for (const field of this._settings.settings || []) {
      groups.get(settingSection(field)).push(field);
    }
    for (const section of BLINK_SETTING_SECTIONS) {
      const fields = groups.get(section.key);
      this.$(`group-${section.key}`).replaceChildren(
        ...fields.map((field) => this._field(stagedField(field, this._draft()))));
      const panel = this.shadowRoot.querySelector(`[data-section="${section.key}"]`);
      panel.hidden = !fields.length && !["general", "privacy"].includes(section.key);
    }
    this._renderDraftActions();
    this.$("status").textContent = (this._settings.settings || []).length
      ? "" : "Nessuna impostazione riconosciuta.";
  }

  _renderSummary() {
    const data = this._settings;
    const temp = temperatureValueText(data.temperature_f, this._hass);
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
    const meta = BLINK_SETTING_META[field.key] || [field.key, "", "general"];
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
      value.textContent = this._value(field.value, unit, field.key); return value;
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
      button.addEventListener("click", () => this._stage(field.key, !field.value)); return button;
    }
    if (field.kind === "select") {
      const select = document.createElement("select"); select.setAttribute("aria-label", label);
      for (const option of field.options) select.add(new Option(BLINK_OPTION_LABELS[option] || option, option));
      select.value = field.value; select.addEventListener("change", () => this._stage(field.key, select.value));
      return select;
    }
    const wrapper = document.createElement("label");
    const input = document.createElement("input"); input.type = "range";
    input.setAttribute("aria-label", label);
    Object.assign(input, { min: field.min, max: field.max, step: field.step, value: field.value });
    const output = document.createElement("span"); output.className = "value";
    output.textContent = this._value(field.value, unit, field.key);
    input.addEventListener("input", () => {
      output.textContent = this._value(Number(input.value), unit, field.key);
    });
    input.addEventListener("change", () => this._stage(field.key, Number(input.value)));
    wrapper.append(input, output); return wrapper;
  }

  _textControl(field, label) {
    const wrapper = document.createElement("div"); wrapper.className = "text-control";
    const input = document.createElement("input"); input.type = "text";
    input.value = field.value; input.maxLength = field.max || 255;
    input.setAttribute("aria-label", label);
    input.addEventListener("input", () => this._stage(field.key, input.value, false));
    wrapper.append(input); return wrapper;
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
      input.addEventListener("change", () => { if (input.checked) this._stage(field.key, option.value); });
      const copy = document.createElement("span");
      const title = document.createElement("strong"); title.textContent = option.label;
      const help = document.createElement("small"); help.textContent = option.description;
      copy.append(title, help); row.append(input, copy); group.append(row);
    }
    return group;
  }

  _value(value, unit, key = "") {
    if (["temperature_min", "temperature_max"].includes(key)) {
      return temperatureValueText(value, this._hass);
    }
    if (typeof value === "boolean") return booleanStateText(value);
    return `${BLINK_OPTION_LABELS[value] || value}${unit ? ` ${unit}` : ""}`;
  }

  _draft() { return cameraDraft(this._drafts, this._camera?.alias || ""); }
  _stage(key, value, render = true) { stageValue(this._settings, this._draft(), key, value);
    if (render) this._render(); else this._renderDraftActions(); }
  _renderDraftActions() { const count = this._draft().size;
    this.$("draft-actions").hidden = count === 0;
    this.$("draft-count").textContent = `${count} ${count === 1 ? "modifica" : "modifiche"} da salvare`;
    this.$("save").textContent = `Salva modifiche (${count})`; }
  _discard() { this._draft().clear(); this._render();
    this.$("status").textContent = "Modifiche locali annullate."; }
  async _saveDraft() {
    const draft = this._draft(); const count = draft.size; if (!count) return;
    if (!globalThis.confirm(`Confermi ${count} ${count === 1 ? "modifica" : "modifiche"} a questa telecamera?`)) return;
    this.$("status").textContent = "Salvataggio e verifica…";
    try { this._settings = await commitDraft(this._hass, this._camera.alias, this._settings, draft);
      draft.clear(); this._render(); this.$("status").textContent = "Modifiche verificate sulla camera.";
    } catch (error) { await this._load(); this.$("status").textContent = error.rollbackFailed
      ? "Salvataggio fallito: rileggi lo stato prima di riprovare."
      : "Salvataggio fallito: le modifiche già inviate sono state ripristinate."; }
  }
}

if (!customElements.get("vistoda-blink-settings")) {
  customElements.define("vistoda-blink-settings", VistodaBlinkSettings);
}
