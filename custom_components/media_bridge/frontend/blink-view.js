import { BASE_STYLES, MEDIA_STYLES } from "./panel-styles.js";
import {
  devicesWithDomain,
  entityState,
  firstEntity,
  openMoreInfo,
  pictureUrl,
  providerDevices,
  setText,
  stateText,
} from "./panel-helpers.js";

class VistodaBlinkView extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._info = null;
    this._index = 0;
    this._nonce = 0;
    this._mounted = false;
  }

  set hass(value) { this._hass = value; this._render(); }
  set info(value) { this._info = value; this._render(); }

  _mount() {
    this._mounted = true;
    this.shadowRoot.innerHTML = `
      <style>${BASE_STYLES}${MEDIA_STYLES}
        #message { min-height:21px; margin-top:12px; }
      </style>
      <section class="provider-head"><div><div class="eyebrow">Vistoda · Blink</div>
        <h2>Telecamere Blink</h2><div class="muted">Gli snapshot esistenti non risvegliano
        le camere. Aggiornamento e live partono soltanto su richiesta.</div></div>
        <span class="badge off" id="availability">Verifica…</span></section>
      <section class="card system" id="system"><div><strong id="system-name">Sistema Blink</strong>
        <div class="muted" id="system-state">Stato non disponibile</div></div>
        <div class="actions"><button id="disarm">Disarma</button>
          <button class="primary" id="arm">Arma fuori casa</button></div></section>
      <section class="card media-card" id="gallery">
        <div class="stage"><div class="placeholder" id="placeholder"><ha-icon icon="mdi:cctv"></ha-icon>
          Snapshot non disponibile</div><img id="snapshot" alt=""></div>
        <div class="media-body"><div class="media-title"><div><h3 id="camera-name">Telecamera</h3>
          <div class="muted" id="camera-position"></div></div><span class="badge off" id="camera-state">
          Non disponibile</span></div>
          <div class="facts"><div class="fact"><span>Batteria</span><strong id="battery">—</strong></div>
            <div class="fact"><span>Temperatura</span><strong id="temperature">—</strong></div>
            <div class="fact"><span>Clip recenti</span><strong id="clips">0</strong></div></div>
          <div class="actions"><button class="primary" id="live">Apri live</button>
            <button id="refresh">Aggiorna snapshot</button><button id="motion">Movimento</button></div>
          <div class="muted" id="message" role="status"></div></div>
      </section>
      <nav class="pager" aria-label="Seleziona telecamera"><button id="previous"
        aria-label="Telecamera precedente">←</button><div class="dots" id="dots"></div>
        <button id="next" aria-label="Telecamera successiva">→</button></nav>`;
    this.$ = (id) => this.shadowRoot.getElementById(id);
    this.$("previous").addEventListener("click", () => this._move(-1));
    this.$("next").addEventListener("click", () => this._move(1));
    this.$("live").addEventListener("click", () => this._openLive());
    this.$("refresh").addEventListener("click", () => this._refreshSnapshot());
    this.$("motion").addEventListener("click", () => this._toggleMotion());
    this.$("arm").addEventListener("click", () => this._setAlarm(true));
    this.$("disarm").addEventListener("click", () => this._setAlarm(false));
    this.$("snapshot").addEventListener("error", () => this._showImage(false));
  }

  _render() {
    if (!this._mounted) this._mount();
    const provider = this._info?.providers?.blink;
    const cameras = this._cameras();
    this._index = Math.min(this._index, Math.max(cameras.length - 1, 0));
    this.$("availability").textContent = provider?.available ? "Operativo" : "Non disponibile";
    this.$("availability").classList.toggle("off", !provider?.available);
    this._renderAlarm();
    this.$("gallery").hidden = cameras.length === 0;
    this.$("previous").disabled = cameras.length < 2;
    this.$("next").disabled = cameras.length < 2;
    if (cameras.length) this._renderCamera(cameras[this._index], cameras.length);
    this._renderDots(cameras.length);
  }

  _cameras() { return devicesWithDomain(this._info, "blink", "camera"); }

  _renderAlarm() {
    const device = providerDevices(this._info, "blink")
      .find((item) => item.entities?.alarm_control_panel?.length);
    const alarm = firstEntity(device, "alarm_control_panel");
    const state = entityState(this._hass, alarm);
    setText(this.shadowRoot, "system-name", device?.name || "Sistema Blink");
    setText(this.shadowRoot, "system-state", state?.state === "armed_away"
      ? "Armato fuori casa" : state?.state === "disarmed" ? "Disarmato" : "Non disponibile");
    this.$("system").hidden = !alarm;
    this.$("arm").disabled = !state || state.state === "armed_away";
    this.$("disarm").disabled = !state || state.state === "disarmed";
  }

  _renderCamera(device, count) {
    const camera = firstEntity(device, "camera");
    const cameraState = entityState(this._hass, camera);
    const battery = firstEntity(device, "binary_sensor", (item) => item.device_class === "battery");
    const temperature = firstEntity(device, "sensor", (item) => item.device_class === "temperature");
    const motion = firstEntity(device, "switch");
    const clips = cameraState?.attributes?.recent_clips || [];
    setText(this.shadowRoot, "camera-name", device.name);
    setText(this.shadowRoot, "camera-position", `${this._index + 1} di ${count}`);
    setText(this.shadowRoot, "camera-state", cameraState && cameraState.state !== "unavailable"
      ? "Disponibile" : "Non disponibile");
    this.$("camera-state").classList.toggle("off", !cameraState || cameraState.state === "unavailable");
    const batteryState = entityState(this._hass, battery);
    setText(this.shadowRoot, "battery", batteryState?.state === "on" ? "Scarica"
      : batteryState?.state === "off" ? "OK" : "Non rilevata");
    setText(this.shadowRoot, "temperature", stateText(this._hass, temperature, "Non rilevata"));
    setText(this.shadowRoot, "clips", String(clips.length));
    const motionState = entityState(this._hass, motion);
    this.$("motion").textContent = motionState?.state === "on"
      ? "Disattiva movimento" : "Attiva movimento";
    this.$("motion").disabled = !motionState || motionState.state === "unavailable";
    const url = pictureUrl(this._hass, camera, this._nonce);
    this.$("snapshot").alt = `Snapshot ${device.name}`;
    if (url && this.$("snapshot").src !== url) this.$("snapshot").src = url;
    this._showImage(Boolean(url));
  }

  _renderDots(count) {
    const dots = Array.from({ length: count }, (_, index) => {
      const button = document.createElement("button");
      button.className = `dot${index === this._index ? " active" : ""}`;
      button.setAttribute("aria-label", `Apri telecamera ${index + 1}`);
      button.addEventListener("click", () => { this._index = index; this._render(); });
      return button;
    });
    this.$("dots").replaceChildren(...dots);
  }

  _move(step) {
    const count = this._cameras().length;
    if (!count) return;
    this._index = (this._index + step + count) % count;
    this._render();
  }

  _current(domain) { return firstEntity(this._cameras()[this._index], domain); }
  _openLive() { openMoreInfo(this, this._current("camera")?.entity_id); }

  async _refreshSnapshot() {
    const camera = this._current("camera");
    await this._action("refresh", async () => {
      await this._hass.callService("blink_live_bridge", "trigger_camera", {
        entity_id: camera.entity_id,
      });
      this._nonce = Date.now();
      this._render();
    }, "Snapshot aggiornato");
  }

  async _toggleMotion() {
    const motion = this._current("switch");
    const turnOn = entityState(this._hass, motion)?.state !== "on";
    await this._action("motion", () => this._hass.callService("switch", turnOn
      ? "turn_on" : "turn_off", { entity_id: motion.entity_id }), "Movimento aggiornato");
  }

  async _setAlarm(armed) {
    const device = providerDevices(this._info, "blink")
      .find((item) => item.entities?.alarm_control_panel?.length);
    const alarm = firstEntity(device, "alarm_control_panel");
    await this._action(armed ? "arm" : "disarm", () => this._hass.callService(
      "alarm_control_panel", armed ? "alarm_arm_away" : "alarm_disarm",
      { entity_id: alarm.entity_id },
    ), armed ? "Sistema armato" : "Sistema disarmato");
  }

  async _action(button, operation, success) {
    const control = this.$(button);
    if (!control) return;
    control.disabled = true;
    setText(this.shadowRoot, "message", "Operazione in corso…");
    try { await operation(); setText(this.shadowRoot, "message", success); }
    catch (_error) { setText(this.shadowRoot, "message", "Operazione non riuscita"); }
    finally { this._render(); }
  }

  _showImage(show) {
    this.$("snapshot").hidden = !show;
    this.$("placeholder").hidden = show;
  }
}

if (!customElements.get("vistoda-blink-view")) {
  customElements.define("vistoda-blink-view", VistodaBlinkView);
}
