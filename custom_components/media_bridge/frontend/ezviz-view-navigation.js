import { copy } from "./panel-copy.js";
import { devicesWithDomain, firstEntity, swipeStep, wrappedIndex } from "./panel-helpers.js";

export const ezvizViewNavigation = {
  _reconcileCameraSelection(cameras) {
    if (this._selectedCameraId) {
      const selectedIndex = cameras.findIndex((device) =>
        firstEntity(device, "camera")?.entity_id === this._selectedCameraId);
      if (selectedIndex >= 0) this._cameraIndex = selectedIndex;
      else {
        this._cameraGeneration += 1; this._selectedCameraId = ""; this._snapshotPending = false;
      }
    }
    this._cameraIndex = Math.min(this._cameraIndex, Math.max(0, cameras.length - 1));
    if (cameras.length && !this._selectedCameraId) {
      this._selectedCameraId = firstEntity(cameras[this._cameraIndex], "camera")?.entity_id || "";
    }
  },

  _renderDots(cameras) {
    const dots = cameras.map((camera, index) => {
      const button = document.createElement("button");
      button.className = `dot${index === this._cameraIndex ? " active" : ""}`;
      const label = copy(this, "Apri telecamera {p0}", { p0: camera.name || index + 1 });
      button.setAttribute("aria-label", label);
      button.title = label;
      if (index === this._cameraIndex) button.setAttribute("aria-current", "true");
      button.addEventListener("click", () => this._selectCamera(index));
      return button;
    });
    this.$("dots").replaceChildren(...dots);
  },

  _selectCamera(index) {
    const cameraId = firstEntity(
      devicesWithDomain(this._info, "ezviz", "camera")[index], "camera",
    )?.entity_id || "";
    if (cameraId === this._selectedCameraId) return;
    this._cameraGeneration += 1; this._cameraIndex = index; this._selectedCameraId = cameraId;
    this._snapshotPending = false; this._imageUrl = ""; this._imageState = "empty";
    this._render();
  },

  _move(step) {
    const count = devicesWithDomain(this._info, "ezviz", "camera").length;
    if (count >= 2) this._selectCamera(wrappedIndex(this._cameraIndex, step, count));
  },

  _startSwipe(event) {
    if (event.isPrimary === false
        || devicesWithDomain(this._info, "ezviz", "camera").length < 2) return;
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
