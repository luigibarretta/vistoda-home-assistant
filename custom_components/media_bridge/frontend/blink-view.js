import { copy, localizeCopy } from "./panel-copy.js";
import "./blink-settings.js";
import "./blink-storage.js";
import "./blink-zones.js";
import "./provider-recordings.js";
import { blinkViewLive } from "./blink-view-live.js";
import { BLINK_VIEW_TEMPLATE } from "./blink-view-template.js";
import { localize, localizeElements } from "./panel-localize.js";
import {
  devicesWithDomain,
  entityState,
  firstEntity,
  pictureUrl,
  providerDevices,
  setText,
  snapshotTimeText,
  stateText,
  swipeStep,
  wrappedIndex,
} from "./panel-helpers.js";

class VistodaBlinkView extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._info = null;
    this._index = 0;
    this._nonce = 0;
    this._failedImage = "";
    this._snapshotTimes = new Map();
    this._swipeStart = null;
    this._detailOpen = false;
    this._liveState = { phase: "idle", microphone: false, speaker: false, message: "" };
    this._liveSession = null;
    this._mounted = false;
  }

  set hass(value) { this._hass = value; this._render(); }
  set info(value) { this._info = value; this._render(); }
  _mount() {
    this._mounted = true;
    this.shadowRoot.innerHTML = BLINK_VIEW_TEMPLATE; localizeCopy(this.shadowRoot, this);
    this.$ = (id) => this.shadowRoot.getElementById(id);
    this.$("previous").addEventListener("click", () => this._move(-1));
    this.$("next").addEventListener("click", () => this._move(1));
    this.$("live").addEventListener("click", () => this._toggleLive());
    this.$("speaker").addEventListener("click", () => this._liveSession?.toggleSpeaker());
    this.$("microphone").addEventListener("click", () => this._liveSession?.toggleMicrophone());
    this.$("refresh").addEventListener("click", () => this._refreshSnapshot());
    this.$("motion").addEventListener("click", () => this._toggleMotion());
    this.$("details").addEventListener("click", () => {
      this._liveSession?.stop(); this._detailOpen = true; this._render();
    });
    this.$("details-back").addEventListener("click", () => { this._detailOpen = false; this._render(); });
    this.$("arm").addEventListener("click", () => this._setAlarm(true));
    this.$("disarm").addEventListener("click", () => this._setAlarm(false));
    this.$("stage").addEventListener("pointerdown", (event) => this._startSwipe(event));
    this.$("stage").addEventListener("pointerup", (event) => this._finishSwipe(event));
    this.$("stage").addEventListener("pointercancel", () => { this._swipeStart = null; });
    this.$("snapshot").addEventListener("error", (event) => {
      this._failedImage = event.currentTarget.src;
      this._showImage(false);
    });
    this.$("snapshot").addEventListener("load", () => {
      this._failedImage = "";
      this._showImage(true);
    });
  }

  _render() {
    if (!this._mounted) this._mount();
    localizeCopy(this.shadowRoot, this);
    localizeElements(this.shadowRoot, this._hass, { provider: "Blink" });
    const provider = this._info?.providers?.blink;
    const cameras = this._cameras();
    this.$("empty").hidden = Boolean(cameras.length);
    this._index = Math.min(this._index, Math.max(cameras.length - 1, 0));
    if (!cameras.length) this._detailOpen = false;
    this.$("availability").textContent = localize(this._hass, provider?.available ? "ready" : "unavailable");
    this.$("availability").classList.toggle("off", !provider?.available);
    this._renderAlarm();
    this.$("provider-head").hidden = this._detailOpen;
    this.$("gallery").hidden = this._detailOpen || cameras.length === 0;
    this.$("pager").hidden = this._detailOpen || cameras.length === 0;
    this.$("details-page").hidden = !this._detailOpen || cameras.length === 0;
    this.$("storage").hidden = this._detailOpen;
    const entry = provider?.entries?.[0] || null;
    this.$("storage").configure(this._hass, entry ? {
      provider: "blink", entryId: entry.entry_id,
    } : null);
    if (this._detailOpen) this.$("system").hidden = true;
    this.$("previous").disabled = cameras.length < 2;
    this.$("next").disabled = cameras.length < 2;
    if (cameras.length) this._renderCamera(cameras[this._index], cameras.length);
    else {
      this.$("settings").camera = null;
      this.$("zones").camera = null;
      this.$("recordings").configure(this._hass, null);
    }
    this._renderDots(cameras.length);
    this._renderLive();
  }

  _cameras() { return devicesWithDomain(this._info, "blink", "camera"); }
  _renderAlarm() {
    const device = providerDevices(this._info, "blink")
      .find((item) => item.entities?.alarm_control_panel?.length);
    const alarm = firstEntity(device, "alarm_control_panel");
    const state = entityState(this._hass, alarm);
    setText(this.shadowRoot, "system-name", device?.name || copy(this, "Sistema Blink"));
    setText(this.shadowRoot, "system-state", state?.state === "armed_away"
      ? copy(this, "Armato fuori casa") : state?.state === "disarmed" ? copy(this, "Disarmato") : copy(this, "Non disponibile"));
    this.$("system").hidden = !alarm;
    this.$("arm").disabled = !state || state.state === "armed_away";
    this.$("disarm").disabled = !state || state.state === "disarmed";
  }

  _renderCamera(device, count) {
    const entry = this._info?.providers?.blink?.entries?.[0] || null;
    const camera = firstEntity(device, "camera");
    const cameraState = entityState(this._hass, camera);
    const battery = firstEntity(device, "binary_sensor", (item) => item.device_class === "battery");
    const temperature = firstEntity(device, "sensor", (item) => item.device_class === "temperature");
    const motion = firstEntity(device, "switch");
    const clips = cameraState?.attributes?.recent_clips || [];
    setText(this.shadowRoot, "camera-name", device.name);
    setText(this.shadowRoot, "details-title", device.name);
    setText(this.shadowRoot, "camera-position", copy(this, "{p0} di {p1}", { p0: this._index + 1, p1: count }));
    setText(this.shadowRoot, "snapshot-time", snapshotTimeText(
      cameraState,
      this._hass?.locale?.language || "it-IT",
      this._snapshotTimes.get(camera?.entity_id),
    ));
    setText(this.shadowRoot, "camera-state", cameraState && cameraState.state !== "unavailable"
      ? copy(this, "Disponibile") : copy(this, "Non disponibile"));
    this.$("camera-state").classList.toggle("off", !cameraState || cameraState.state === "unavailable");
    const batteryState = entityState(this._hass, battery);
    setText(this.shadowRoot, "battery", batteryState?.state === "on" ? copy(this, "Batteria scarica")
      : batteryState?.state === "off" ? "OK" : copy(this, "Non rilevata"));
    this.$("battery-icon").setAttribute("icon", batteryState?.state === "on"
      ? "mdi:battery-alert-variant-outline" : "mdi:battery");
    setText(this.shadowRoot, "temperature", stateText(this._hass, temperature, copy(this, "Non rilevata")));
    setText(this.shadowRoot, "clips", String(clips.length));
    const motionState = entityState(this._hass, motion);
    const motionEnabled = motionState?.state === "on";
    setText(this.shadowRoot, "motion-label", motionEnabled
      ? copy(this, "Disattiva movimento") : copy(this, "Attiva movimento"));
    this.$("motion-icon").setAttribute("icon", motionEnabled
      ? "mdi:motion-sensor-off" : "mdi:motion-sensor");
    this.$("motion").disabled = !motionState || motionState.state === "unavailable";
    const url = pictureUrl(this._hass, camera, this._nonce);
    if (this._liveSession) this._liveSession.hass = this._hass;
    this.$("snapshot").alt = copy(this, "Snapshot {p0}", { p0: device.name });
    this.$("settings").hass = this._hass;
    this.$("settings").camera = { alias: cameraState?.attributes?.alias, name: device.name };
    this.$("recordings").configure(this._hass, {
      provider: "blink", entryId: entry?.entry_id, alias: cameraState?.attributes?.alias,
    });
    this.$("zones").hass = this._hass;
    if (url && this.$("snapshot").src !== url) {
      this._failedImage = "";
      this.$("snapshot").src = url;
    }
    this.$("zones").camera = { alias: cameraState?.attributes?.alias, name: device.name, snapshot: url };
    this._showImage(Boolean(url) && this._failedImage !== url);
  }

  _renderDots(count) {
    const dots = Array.from({ length: count }, (_, index) => {
      const button = document.createElement("button");
      button.className = `dot${index === this._index ? " active" : ""}`;
      button.setAttribute("aria-label", copy(this, "Apri telecamera {p0}", { p0: index + 1 }));
      button.title = copy(this, "Apri telecamera {p0}", { p0: index + 1 });
      if (index === this._index) button.setAttribute("aria-current", "true");
      button.addEventListener("click", () => {
        this._liveSession?.stop(); this._index = index; this._render();
      });
      return button;
    });
    this.$("dots").replaceChildren(...dots);
  }

  _move(step) {
    const count = this._cameras().length;
    if (!count) return;
    this._liveSession?.stop();
    this._index = wrappedIndex(this._index, step, count);
    this._render();
  }

  _startSwipe(event) {
    if (event.isPrimary === false || this._cameras().length < 2) return;
    this._swipeStart = { id: event.pointerId, x: event.clientX, y: event.clientY };
  }

  _finishSwipe(event) {
    const start = this._swipeStart;
    this._swipeStart = null;
    if (!start || start.id !== event.pointerId) return;
    const step = swipeStep(start, { x: event.clientX, y: event.clientY });
    if (step) this._move(step);
  }

  _current(domain) { return firstEntity(this._cameras()[this._index], domain); }

  async _refreshSnapshot() {
    const camera = this._current("camera");
    await this._action("refresh", async () => {
      await this._hass.callService("blink_live_bridge", "trigger_camera", {
        entity_id: camera.entity_id,
      });
      this._snapshotTimes.set(camera.entity_id, Date.now());
      this._nonce = Date.now();
      this._render();
    }, copy(this, "Snapshot aggiornato"));
  }

  async _toggleMotion() {
    const motion = this._current("switch");
    const turnOn = entityState(this._hass, motion)?.state !== "on";
    await this._action("motion", () => this._hass.callService("switch", turnOn
      ? "turn_on" : "turn_off", { entity_id: motion.entity_id }), copy(this, "Movimento aggiornato"));
  }

  async _setAlarm(armed) {
    const device = providerDevices(this._info, "blink")
      .find((item) => item.entities?.alarm_control_panel?.length);
    const alarm = firstEntity(device, "alarm_control_panel");
    await this._action(armed ? "arm" : "disarm", () => this._hass.callService(
      "alarm_control_panel", armed ? "alarm_arm_away" : "alarm_disarm",
      { entity_id: alarm.entity_id },
    ), armed ? copy(this, "Sistema armato") : copy(this, "Sistema disarmato"));
  }

  async _action(button, operation, success) {
    const control = this.$(button);
    if (!control) return;
    control.disabled = true;
    setText(this.shadowRoot, "message", copy(this, "Operazione in corso…"));
    try { await operation(); setText(this.shadowRoot, "message", success); }
    catch (_error) { setText(this.shadowRoot, "message", copy(this, "Operazione non riuscita")); }
    finally { this._render(); }
  }
}

Object.assign(VistodaBlinkView.prototype, blinkViewLive);

if (!customElements.get("vistoda-blink-view")) {
  customElements.define("vistoda-blink-view", VistodaBlinkView);
}
