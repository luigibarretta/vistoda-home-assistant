import { copy } from "./panel-copy.js";

export const blinkStorageUi = {
  _fact(icon, labelText, valueText) {
    const node = document.createElement("span"); node.className = "storage-fact"; node.tabIndex = 0;
    const full = `${labelText}: ${valueText}`; node.setAttribute("aria-label", full); node.dataset.tooltip = full;
    const glyph = document.createElement("ha-icon"); glyph.setAttribute("icon", icon);
    const label = document.createElement("span"); label.textContent = valueText;
    node.append(glyph, label); return node;
  },
  _storageGauge(value) {
    const used = Math.max(0, Math.min(100, Number(value)));
    const node = document.createElement("div"); node.className = "storage-gauge";
    const label = copy(this, "Spazio utilizzato: {p0}%", { p0: used });
    node.setAttribute("role", "img"); node.setAttribute("aria-label", label); node.dataset.tooltip = label;
    node.tabIndex = 0; node.style.setProperty("--used", `${used * 3.6}deg`);
    const valueNode = document.createElement("strong"); valueNode.textContent = `${used}%`;
    node.append(valueNode); return node;
  },
  _moduleAction(icon, label, reason, danger = false) {
    const button = this._icon(icon, label, () => {}, false, danger);
    button.disabled = true;
    button.setAttribute("aria-disabled", "true");
    button.dataset.tooltip = reason; button.removeAttribute("title"); return button;
  },
};
