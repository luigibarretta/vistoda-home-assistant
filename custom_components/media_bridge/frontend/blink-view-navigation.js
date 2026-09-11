import { copy } from "./panel-copy.js";
import { entityState, firstEntity, providerDevices, setText, swipeStep,
  wrappedIndex } from "./panel-helpers.js";

export const blinkViewNavigation = {
  _alarmDevice() {
    const alarms = providerDevices(this._info, "blink")
      .filter((item) => item.entities?.alarm_control_panel?.length);
    const cameraState = entityState(this._hass, this._current("camera"));
    const networkId = cameraState?.attributes?.network_id;
    const exact = networkId == null ? null : alarms.find((item) => {
      const state = entityState(this._hass, firstEntity(item, "alarm_control_panel"));
      return String(state?.attributes?.network_id) === String(networkId);
    });
    return exact || (networkId == null && alarms.length === 1 ? alarms[0] : null);
  },

  _renderAlarm() {
    const device = this._alarmDevice();
    const alarm = firstEntity(device, "alarm_control_panel");
    const state = entityState(this._hass, alarm);
    setText(this.shadowRoot, "system-name", device?.name || copy(this, "Sistema Blink"));
    setText(this.shadowRoot, "system-state", state?.state === "armed_away"
      ? copy(this, "Armato fuori casa") : state?.state === "disarmed"
        ? copy(this, "Disarmato") : copy(this, "Non disponibile"));
    this.$("system").hidden = !alarm;
    this.$("arm").disabled = !state || state.state === "armed_away";
    this.$("disarm").disabled = !state || state.state === "disarmed";
  },

  _renderDots(count) {
    const dots = Array.from({ length: count }, (_, index) => {
      const button = document.createElement("button");
      button.className = `dot${index === this._index ? " active" : ""}`;
      button.setAttribute("aria-label", copy(this, "Apri telecamera {p0}", { p0: index + 1 }));
      button.title = copy(this, "Apri telecamera {p0}", { p0: index + 1 });
      if (index === this._index) button.setAttribute("aria-current", "true");
      button.addEventListener("click", () => this._selectCamera(index));
      return button;
    });
    this.$("dots").replaceChildren(...dots);
  },

  _move(step) {
    const count = this._cameras().length;
    if (count) this._selectCamera(wrappedIndex(this._index, step, count));
  },

  _selectCamera(index) {
    const camera = firstEntity(this._cameras()[index], "camera");
    const entityId = camera?.entity_id || "";
    if (entityId === this._selectedCameraId) return;
    this._stopLiveForCameraChange();
    this._index = index; this._selectedCameraId = entityId; this._detailOpen = false;
    this._render();
  },

  _stopLiveForCameraChange() {
    const session = this._liveSession;
    this._liveSession = null;
    this._liveState = { phase: "idle", microphone: false, speaker: false,
      legacyAvailable: false, message: "" };
    session?.stop(false);
  },

  _startSwipe(event) {
    if (event.isPrimary === false || this._cameras().length < 2) return;
    this._swipeStart = { id: event.pointerId, x: event.clientX, y: event.clientY };
  },

  _finishSwipe(event) {
    const start = this._swipeStart;
    this._swipeStart = null;
    if (!start || start.id !== event.pointerId) return;
    const step = swipeStep(start, { x: event.clientX, y: event.clientY });
    if (step) this._move(step);
  },
};
