import { copy, localizeCopy } from "./panel-copy.js";
import { BASE_STYLES } from "./panel-styles.js";
import { ARCHIVE_SELECT_STYLE } from "./archive-layout-styles.js";
import { BATTERY_NOTICE, DELAY_NOTE, batteryCameras, draftChanged, draftValid, motionDraft,
  motionError, motionPayload, pollerStatus, toggleCamera } from "./blink-motion-model.js";

// Blink motion-triggered HA-local recording settings, owned by the Blink HA
// adapter. Older adapters answer `unknown_command`: the card then stays hidden.
const REFRESH_MS = 60_000;
const STYLES = `
  :host { display:block; margin:0 0 16px; min-width:0; } :host([hidden]) { display:none !important; }
  .card { padding:16px; display:grid; gap:10px; min-width:0; }
  h4 { display:flex; align-items:center; gap:8px; margin:0; font-size:17px; }
  p { margin:0; }
  .check { display:flex; align-items:center; gap:10px; min-height:44px; cursor:pointer; min-width:0; }
  .check input { flex:0 0 22px; width:22px; height:22px; margin:0; accent-color:var(--primary-color); }
  .check input:disabled { cursor:not-allowed; }
  .field { display:grid; gap:6px; }
  .field label, legend { color:var(--secondary-text-color); font-size:13px; font-weight:650; }
  select { ${ARCHIVE_SELECT_STYLE} width:100%; max-width:240px; }
  fieldset { min-width:0; margin:0; padding:0; border:0; }
  .cameras { display:grid; grid-template-columns:repeat(auto-fill,minmax(min(180px,100%),1fr)); gap:0 12px; }
  .battery-tag { color:var(--secondary-text-color); font-size:12px; }
  .notice { display:flex; align-items:flex-start; gap:8px; padding:10px 12px; border-radius:12px;
    background:color-mix(in srgb,var(--warning-color,#ffa600) 16%,transparent); }
  .notice ha-icon { flex:0 0 auto; --mdc-icon-size:20px; }
  .footer { display:flex; flex-wrap:wrap; align-items:center; justify-content:space-between; gap:10px; }
  @media (max-width:420px) { select { max-width:none; } .footer button { flex:1 1 100%; } }
`;

class VistodaBlinkMotionRecording extends HTMLElement {
  constructor() {
    super(); this.attachShadow({ mode: "open" }); this.hidden = true; this._generation = 0;
    this.shadowRoot.innerHTML = `<style>${BASE_STYLES}${STYLES}</style>
      <section class="card" aria-labelledby="title"><h4 id="title"><ha-icon icon="mdi:motion-sensor"></ha-icon>
        <span data-copy="Registrazione al movimento">Registrazione al movimento</span></h4>
        <p class="muted" id="poller"></p>
        <label class="check"><input id="enabled" type="checkbox" role="switch">
          <span data-copy="Registra nell’archivio Locale HA quando Blink rileva un movimento">Registra nell’archivio Locale HA quando Blink rileva un movimento</span></label>
        <div class="field"><label for="duration" data-copy="Durata">Durata</label><select id="duration">
          <option value="15" data-copy="15 secondi">15 secondi</option><option value="30" data-copy="30 secondi">30 secondi</option>
          <option value="60" data-copy="60 secondi">60 secondi</option></select></div>
        <fieldset><legend data-copy="Telecamere">Telecamere</legend>
          <label class="check"><input id="all" type="checkbox"><span data-copy="Tutte le telecamere">Tutte le telecamere</span></label>
          <div class="cameras" id="cameras"></div></fieldset>
        <p class="notice" id="battery" hidden><ha-icon icon="mdi:battery-alert-variant-outline"></ha-icon>
          <span><span data-copy="${BATTERY_NOTICE}">${BATTERY_NOTICE}</span> <strong id="battery-names"></strong></span></p>
        <p class="muted" data-copy="${DELAY_NOTE}">${DELAY_NOTE}</p>
        <p class="muted" id="admin-note" hidden data-copy="Solo un amministratore di Home Assistant può modificare queste impostazioni.">Solo un amministratore di Home Assistant può modificare queste impostazioni.</p>
        <div class="footer"><span class="muted" id="message" role="status"></span>
          <button class="primary" id="save"><ha-icon icon="mdi:content-save-outline"></ha-icon><span data-copy="Salva">Salva</span></button></div>
      </section>`;
    this.$ = (id) => this.shadowRoot.getElementById(id);
    this.$("enabled").onchange = () => this._edit({ enabled: this.$("enabled").checked });
    this.$("duration").onchange = () => this._edit({ duration_seconds: Number(this.$("duration").value) });
    this.$("all").onchange = () => this._edit(this.$("all").checked ? { all: true, cameras: [] }
      : { all: false, cameras: this._cameras().map((camera) => camera.alias) });
    this.$("save").onclick = () => this._save();
  }
  configure(hass, entryId) {
    this._hass = hass; localizeCopy(this.shadowRoot, this);
    const stale = Date.now() - (this._loadedAt || 0) > REFRESH_MS;
    if (entryId !== this._entryId) {
      this._entryId = entryId; this._generation++; this._state = null; this._draft = null;
      this._unsupported = false; this._busy = false; this.hidden = true; this._setMessage("");
      if (entryId) this.load();
    } else if (entryId && stale && !this._busy && !this._unsupported && !this._dirty()) this.load();
    this._render();
  }
  async load() {
    const generation = this._generation; this._loadedAt = Date.now();
    try {
      const result = await this._hass.callWS({ type: "blink_live_bridge/motion_recording/get" });
      if (generation !== this._generation) return;
      this._apply(result, this._dirty());
    } catch (error) {
      if (generation !== this._generation) return;
      // Only a successful read shows the card; an older adapter is never retried.
      if (error?.code === "unknown_command") this._unsupported = true;
      this._state = null; this.hidden = true;
    }
  }
  _apply(result, keepDraft = false) {
    this._state = result || {}; this.hidden = false;
    if (!keepDraft) this._draft = motionDraft(this._state.settings);
    this._render();
  }
  _cameras() { return Array.isArray(this._state?.cameras) ? this._state.cameras : []; }
  _admin() { return this._hass?.user?.is_admin === true; }
  _dirty() { return Boolean(this._draft && this._state) && draftChanged(this._draft, this._state.settings); }
  _edit(change) { this._draft = { ...this._draft, ...change }; this._setMessage(""); this._render(); }
  _render() {
    if (!this._draft || !this._state) return;
    const locked = !this._admin() || this._busy, draft = this._draft, cameras = this._cameras();
    const [status, values] = pollerStatus(this._state.poller);
    this.$("poller").textContent = copy(this, status, values);
    this.$("enabled").checked = draft.enabled; this.$("enabled").disabled = locked;
    // Rewriting an unchanged value on HA state pushes can dismiss an open mobile picker.
    const duration = this.$("duration"), value = String(draft.duration_seconds);
    if (duration.value !== value) duration.value = value;
    duration.disabled = locked;
    this.$("all").checked = draft.all; this.$("all").disabled = locked;
    this._renderCameras(cameras, locked);
    const battery = batteryCameras(draft, cameras);
    this.$("battery").hidden = !battery.length;
    this.$("battery-names").textContent = battery.map((camera) => camera.name || camera.alias).join(", ");
    this.$("admin-note").hidden = this._admin();
    const valid = draftValid(draft);
    if (!valid) this._setMessage(copy(this, "Seleziona almeno una telecamera."));
    this.$("save").disabled = locked || !valid || !this._dirty();
  }
  _renderCameras(cameras, locked) {
    const key = JSON.stringify(cameras.map((camera) => [camera.alias, camera.name, camera.powered]));
    if (key !== this._camerasKey) {
      this._camerasKey = key;
      this.$("cameras").replaceChildren(...cameras.map((camera) => {
        const label = document.createElement("label"), input = document.createElement("input");
        const name = document.createElement("span"); label.className = "check";
        input.type = "checkbox"; input.dataset.alias = camera.alias;
        input.onchange = () => { this._draft = toggleCamera(this._draft, this._cameras(), camera.alias, input.checked);
          this._setMessage(""); this._render(); };
        name.textContent = camera.name || camera.alias; label.append(input, name);
        if (camera.powered === false) {
          const tag = document.createElement("span"); tag.className = "battery-tag";
          tag.textContent = `· ${copy(this, "a batteria")}`; label.append(tag);
        }
        return label;
      }));
    }
    for (const input of this.$("cameras").querySelectorAll("input")) {
      input.checked = this._draft.all || this._draft.cameras.includes(input.dataset.alias);
      input.disabled = locked;
    }
  }
  async _save() {
    if (this._busy || !this._admin() || !draftValid(this._draft)) return;
    const generation = this._generation;
    this._busy = true; this._setMessage(copy(this, "Salvataggio…")); this._render();
    try {
      const result = await this._hass.callWS(motionPayload(this._draft));
      if (generation !== this._generation) return;
      this._busy = false; this._apply(result); this._loadedAt = Date.now();
      this._setMessage(copy(this, "Impostazioni di registrazione salvate."));
    } catch (error) {
      if (generation !== this._generation) return;
      this._busy = false; this._render(); this._setMessage(copy(this, motionError(error)));
    }
  }
  _setMessage(text) { this.$("message").textContent = text; }
}
if (!customElements.get("vistoda-blink-motion-recording")) {
  customElements.define("vistoda-blink-motion-recording", VistodaBlinkMotionRecording);
}
