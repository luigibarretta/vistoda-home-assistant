import { copy } from "./panel-copy.js";

export const blinkStorageFilter = {
  _renderCameraFilter() {
    const options = this._cameraNames.map((name) => {
      const label = document.createElement("label");
      const input = document.createElement("input");
      input.type = "checkbox";
      input.checked = this._cameraFilter.has(name);
      input.disabled = this._busy;
      input.addEventListener("change", async () => {
        input.checked ? this._cameraFilter.add(name) : this._cameraFilter.delete(name);
        this._page = 1;
        this._selected.clear();
        await this.reload();
      });
      const text = document.createElement("span");
      text.textContent = name;
      label.append(input, text);
      return label;
    });
    this.$("camera-filter-options").replaceChildren(...options);
    this.$("camera-filter").hidden = this._cameraNames.length < 2;
    this.$("camera-filter-label").textContent = this._cameraFilter.size
      ? copy(this, "{p0} telecamere selezionate", { p0: this._cameraFilter.size })
      : copy(this, "Tutte le telecamere");
  },
};
