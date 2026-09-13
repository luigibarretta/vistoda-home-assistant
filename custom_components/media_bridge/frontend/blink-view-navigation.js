import { copy } from "./panel-copy.js";
import { dragStart, dragMove, dragReset } from "./page-drag.js";
import { circularPagerIndexes, entityState, firstEntity, providerDevices, swipeStep,
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
    this.$("system").hidden = this._detailOpen;
    this.$("system-controls").hidden = !alarm;
    this.$("system-controls").configure(this._hass, alarm?.entity_id, device?.name || copy(this, "Sistema Blink"));
  },

  _renderDots(count) {
    const indexes = circularPagerIndexes(this._index, count);
    const dots = indexes.map((index, position) => {
      const button = document.createElement("button");
      const edge = indexes.length === 3 && position !== 1 ? " edge" : "";
      button.className = `dot${index === this._index ? " active" : ""}${edge}`;
      button.setAttribute("aria-label", copy(this, "Apri telecamera {p0}", { p0: index + 1 }));
      button.title = copy(this, "Apri telecamera {p0}", { p0: index + 1 });
      if (index === this._index) button.setAttribute("aria-current", "true");
      button.addEventListener("click", () => this._selectCamera(index));
      return button;
    });
    this.$("dots").replaceChildren(...dots);
    const direction = this._pagerDirection;
    this._pagerDirection = 0;
    if (direction) {
      const className = direction > 0 ? "pager-next" : "pager-previous";
      this.$("dots").classList.add(className);
      setTimeout(() => this.$("dots")?.classList.remove(className), 240);
    }
  },

  _move(step) {
    const count = this._cameras().length;
    if (count) { this._pagerDirection = Math.sign(step); this._selectCamera(wrappedIndex(this._index, step, count)); }
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
    this._liveOpening = false;
    this._liveControls?.reset();
    this._fullscreen?.exit().catch(() => {});
    const session = this._liveSession;
    this._liveSession = null;
    this._liveState = { phase: "idle", microphone: false, speaker: false,
      legacyAvailable: false, message: "" };
    session?.stop(false);
  },

  _startSwipe(event) {
    if (this._liveSession?.active || this._liveOpening) return;
    if (event.isPrimary === false || this._cameras().length < 2) return;
    dragStart(this, event);
  },

  _dragSwipe(event) { dragMove(this, event); },
  _cancelSwipe() { dragReset(this); },

  _finishSwipe(event) {
    const start = this._swipeStart;
    this._swipeStart = null;
    if (!start || start.id !== event.pointerId) return;
    const step = swipeStep(start, { x: event.clientX, y: event.clientY });
    if (step) this._move(step);
    dragReset(this, step);
  },
};
