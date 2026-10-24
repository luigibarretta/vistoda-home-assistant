import { copy } from "./panel-copy.js";

// The bridge's default recording bound; a longer clip is saved from its start.
export const SD_SAVE_SECONDS = 120;

/** The interval actually requested for one listed microSD clip. */
export function saveInterval(row) {
  const end = Math.min(row.end, row.start + SD_SAVE_SECONDS);
  return { start: row.start, end: end > row.start ? end : row.start + 10 };
}

/** Save buttons for <vistoda-ezviz-media>; the clip lands in local recordings. */
export const SD_SAVE = {
  _saveButton(row) {
    const button = document.createElement("button");
    button.className = "save";
    button.innerHTML = '<ha-icon icon="mdi:content-save-outline"></ha-icon><span></span>';
    button.querySelector("span").textContent = copy(this, "Salva");
    button.setAttribute("aria-label", copy(this, "Salva la clip delle {p0} nell’archivio", { p0: row.text }));
    button.addEventListener("click", () => this._saveClip(row, button));
    return button;
  },

  async _saveClip(row, button) {
    const status = this.shadowRoot.getElementById("save-status");
    button.disabled = true;
    status.textContent = copy(this, "Salvataggio della clip…");
    try {
      await this._hass.callWS({ type: "media_bridge/ezviz/recordings/create_sd", entry_id: this._entryId,
        ...saveInterval(row), request_id: globalThis.crypto.randomUUID() });
      status.textContent = copy(this, "Clip in salvataggio: comparirà nelle registrazioni locali.");
      this.dispatchEvent(new CustomEvent("vistoda-sd-saved", { bubbles: true, composed: true }));
    } catch (error) {
      status.textContent = copy(this, {
        live_active: "Chiudi il live per salvare la clip.",
        conflict: "Un’altra registrazione di questa telecamera è in corso.",
      }[error?.code] || "Impossibile salvare la clip.");
      button.disabled = false;
    }
  },
};
