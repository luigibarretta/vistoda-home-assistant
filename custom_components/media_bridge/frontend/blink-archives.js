import { copy } from "./panel-copy.js";
import { entityState, firstEntity } from "./panel-helpers.js";

export class BlinkArchives {
  constructor(view) {
    this.view = view;
    view.$("local-camera-filter").addEventListener("change", () => this.local());
    view.$("local-archive-panel").pausePlayback = () => view.$("recordings").pausePlayback();
    view.$("usb-archive-panel").pausePlayback = () => view.$("storage").pausePlayback();
    view.$("module-filter").addEventListener("change", () => {
      const storage = view.$("storage"); storage.pausePlayback(); storage._selected.clear();
      storage._moduleFilter = view.$("module-filter").value; storage._render();
    });
  }
  configure(entry, cameras) {
    const view = this.view; this.entry = entry;
    view.$("archives").hidden = view._detailOpen;
    view.$("archive-tabs").hass = view._hass;
    const config = entry ? { provider: "blink", entryId: entry.entry_id } : null;
    view.$("storage").configure(view._hass, config);
    const modules = [["", copy(view, "Tutti i Sync Module")],
      ...view.$("storage")._storages.map((item) => [String(item.sync_module_id), item.name || item.network_name || String(item.sync_module_id)])];
    if (JSON.stringify(modules) !== this.moduleKey) {
      this.moduleKey = JSON.stringify(modules); const select = view.$("module-filter"), selected = select.value;
      select.replaceChildren(...modules.map(([id, name]) => {
        const option = document.createElement("option"); option.value = id; option.textContent = name; return option;
      })); select.value = modules.some(([id]) => id === selected) ? selected : "";
      view.$("storage")._moduleFilter = select.value;
    }
    view.$("network-archive").configure(view._hass, entry?.entry_id);
    const choices = [["", copy(view, "Tutte le telecamere")], ...cameras.map((device) => [
      entityState(view._hass, firstEntity(device, "camera"))?.attributes?.alias, device.name,
    ]).filter(([alias]) => alias)];
    const key = JSON.stringify(choices), select = view.$("local-camera-filter");
    if (key !== this.choicesKey) {
      const selected = select.value; this.choicesKey = key;
      select.replaceChildren(...choices.map(([alias, name]) => {
        const option = document.createElement("option"); option.value = alias; option.textContent = name; return option;
      }));
      select.value = choices.some(([alias]) => alias === selected) ? selected : "";
    }
    this.local();
    if (view._detailOpen) {
      view.$("recordings").pausePlayback(); view.$("storage").pausePlayback();
      view.$("network-archive").pausePlayback();
    }
  }
  local() {
    this.view.$("recordings").configure(this.view._hass, this.entry ? {
      provider: "blink", entryId: this.entry.entry_id,
      alias: this.view.$("local-camera-filter").value || undefined,
    } : null);
  }
}
