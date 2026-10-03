import { copy } from "./panel-copy.js";

// Hourly NFS backup switch for the network archive tab; the option is read
// live by the Home Assistant worker, so no integration reload is involved.
const STORAGE_REASONS = Object.freeze({
  network_mount_missing: "Archivio di rete non montato: aggiungilo in Impostazioni → Sistema → Archiviazione.",
  network_mount_not_writable: "Archivio di rete in sola lettura: verifica i permessi di scrittura.",
  network_mount_low_space: "Spazio insufficiente sull’archivio di rete.",
  network_mount_unavailable: "Archivio di rete non raggiungibile.",
  invalid_storage_name: "Nome dell’archivio di rete non valido nelle opzioni dell’integrazione.",
});

/** Maps a `media_bridge/blink/auto_backup/set` error to an authored message. */
export function autoBackupError(error) {
  if (error?.code === "storage_unavailable") {
    return STORAGE_REASONS[error.message] || "Archivio di rete non pronto per il backup automatico.";
  }
  if (error?.code === "unauthorized") return "Serve un account amministratore di Home Assistant.";
  return "Impossibile aggiornare il backup automatico.";
}

/** Returns the hint shown under the switch for the current role and state. */
export function autoBackupHint(admin, automatic) {
  if (!admin) return "Solo un amministratore di Home Assistant può modificare il backup automatico.";
  if (!automatic) return "Stato del backup automatico non disponibile.";
  return "Ogni ora copia e verifica le clip USB Blink e le registrazioni Locale HA pronte.";
}

export const AUTO_BACKUP_TEMPLATE = `<label class="auto-backup" for="auto-backup">
  <input id="auto-backup" type="checkbox" role="switch" disabled aria-describedby="auto-hint">
  <span><strong data-copy="Backup automatico orario su NFS">Backup automatico orario su NFS</strong>
  <span class="muted" id="auto-hint"></span></span></label>`;

export const AUTO_BACKUP_STYLES = `
  .auto-backup { display:flex; align-items:center; gap:12px; min-height:44px; margin:12px 0;
    padding:10px 12px; border-radius:13px; background:var(--secondary-background-color); cursor:pointer; }
  .auto-backup input { flex:0 0 22px; width:22px; height:22px; margin:0; accent-color:var(--primary-color); }
  .auto-backup input:disabled { cursor:not-allowed; }
  .auto-backup > span { display:grid; gap:2px; min-width:0; }
`;

export const networkArchiveAuto = {
  _admin() { return this._hass?.user?.is_admin === true; },
  _renderAutomatic() {
    const input = this.$("auto-backup");
    // While a change is in flight the switch keeps showing the requested state.
    if (!this._autoBusy) input.checked = Boolean(this._automatic?.enabled);
    input.disabled = this._autoBusy || !this._admin() || !this._automatic;
    this.$("auto-hint").textContent = copy(this, autoBackupHint(this._admin(), this._automatic));
  },
  async _setAutomatic() {
    const input = this.$("auto-backup"), enabled = input.checked, entryId = this.entryId;
    if (this._autoBusy || !this._automatic || !entryId) return;
    this._autoBusy = true; this._renderAutomatic();
    this.$("status").textContent = copy(this, "Aggiornamento backup automatico…");
    let message;
    try {
      await this._hass.callWS({ type: "media_bridge/blink/auto_backup/set", entry_id: entryId, enabled });
      if (entryId !== this.entryId) return;
      this._automatic = { ...this._automatic, enabled };
      message = enabled ? "Backup automatico orario attivato." : "Backup automatico orario disattivato.";
    } catch (error) {
      if (entryId !== this.entryId) return;
      message = autoBackupError(error);
    } finally {
      this._autoBusy = false;
      if (entryId === this.entryId) this._renderAutomatic();
    }
    this.$("status").textContent = copy(this, message);
  },
};
