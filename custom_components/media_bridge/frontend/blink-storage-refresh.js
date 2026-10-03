import { copy } from "./panel-copy.js";
import { usbBlocked, usbNotice } from "./blink-storage-state.js";

// The official storage screens re-read status every 30 s while open and after
// every command. The status-only call never asks the Sync Module for a manifest.
export const STATUS_REFRESH_MS = 30_000;
const PROGRESS = Object.freeze({ eject: "Espulsione in sicurezza…", mount: "Collegamento…" });

const storageKey = (storage) => `${storage.network_id}:${storage.sync_module_id}`;

/** Maps an HA WebSocket error to the outcome the user can act on. */
export function commandErrorMessage(error, fallback) {
  const messages = {
    rejected: "Blink ha rifiutato il comando del Sync Module.",
    pending: "Blink non ha ancora confermato il comando: lo stato si aggiornerà automaticamente.",
    invalid_state: "Lo stato della chiavetta è cambiato: stato aggiornato.",
    unauthorized: "Serve un account amministratore di Home Assistant.",
  };
  return messages[error?.code] || fallback;
}

export const blinkStorageRefresh = {
  connectedCallback() {
    clearInterval(this._statusTimer);
    this._statusTimer = setInterval(() => this._refreshStatus(), STATUS_REFRESH_MS);
  },
  disconnectedCallback() { clearInterval(this._statusTimer); this._statusTimer = null; },

  async _refreshStatus() {
    if (!this._hass || this._busy || !this._loaded || this._statusUnsupported) return;
    if (document.hidden || this.checkVisibility?.() === false) return;
    let result;
    try { result = await this._hass.callWS({ type: "blink_live_bridge/local_storage/status" }); }
    catch (error) {
      // An older adapter has no status command: keep the manual reload only.
      if (error?.code === "unknown_command") this._statusUnsupported = true;
      return;
    }
    if (this._busy) return;
    const fresh = new Map((result?.storages || []).map((storage) => [storageKey(storage), storage]));
    const changed = this._storages.some((storage) => {
      const next = fresh.get(storageKey(storage));
      return next && next.status?.usb_state !== storage.status?.usb_state;
    });
    // A state change can make the index readable or stale: rebuild it once.
    if (changed) { await this.reload(); return; }
    for (const storage of this._storages) {
      const next = fresh.get(storageKey(storage));
      if (next?.status) storage.status = next.status;
    }
    this._render();
  },

  async _storageCommand(storage, command) {
    if (this._busy || !this._hass) return;
    this._busy = true; this._render(); this._setMessage(copy(this, PROGRESS[command]));
    let message = "";
    try {
      await this._hass.callWS({ type: "blink_live_bridge/local_storage/command", command,
        network_id: Number(storage.network_id), sync_module_id: Number(storage.sync_module_id) });
    } catch (error) {
      message = commandErrorMessage(error, "Comando USB non riuscito: Sync Module non raggiungibile.");
    } finally { this._busy = false; await this.reload(); }
    // The native app shows no success text: the refreshed state is the outcome.
    this._setMessage(message ? copy(this, message) : "");
  },

  /** Native format result: success only when the refreshed drive is usable. */
  _formatOutcome(storage) {
    const fresh = this._storages.find((item) => storageKey(item) === storageKey(storage));
    if (fresh && !usbBlocked(fresh)) return copy(this, "Formattazione riuscita!");
    const notice = fresh && usbNotice(fresh);
    return notice
      ? copy(this, "Formattazione inviata, ma Blink segnala ancora: {p0}", { p0: copy(this, notice.title) })
      : copy(this, "Formattazione inviata: stato della chiavetta non ancora disponibile.");
  },
};
