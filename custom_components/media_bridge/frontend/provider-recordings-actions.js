import { backupRecording, readyRecordings } from "./provider-recording-backup.js";
import { recordingMediaPath } from "./provider-recording-model.js";

export const providerRecordingActions = {
  async _start() {
    if (!this._config || this._busy) return;
    const duration = Number(this.$("duration").value);
    if (!globalThis.confirm(`Registrare ${duration} secondi del live in archivio locale?`)) return;
    this._busy = true; this._setMessage("Avvio registrazione…"); this._render();
    try {
      await this._hass.callWS({ ...this._message("create"), duration_seconds: duration,
        request_id: globalThis.crypto.randomUUID() });
      this._setMessage(`Registrazione di ${duration} secondi avviata.`);
    } catch (_error) {
      this._setMessage("Registrazione non avviata: verifica live, disponibilità e quota.");
    } finally { this._busy = false; await this.reload(); }
  },

  async _delete(item) {
    if (!globalThis.confirm("Eliminare definitivamente questa registrazione locale?")) return;
    this._busy = true; this._render();
    const mediaId = `local:${item.recording_id}`;
    try {
      await this._hass.callWS({ ...this._message("delete"), recording_id: item.recording_id });
      this._selected.delete(item.recording_id);
      await this._listManager.forget(mediaId);
      this._setMessage("Registrazione eliminata.");
    } catch (_error) {
      this._setMessage("La registrazione non può essere eliminata mentre è attiva.");
    } finally { this._busy = false; await this.reload(); }
  },

  async _deleteSelected() {
    const items = this._items.filter((item) => this._selected.has(item.recording_id)
      && !["pending", "recording"].includes(item.status));
    if (!items.length) return;
    if (!globalThis.confirm(`Eliminare definitivamente ${items.length} registrazioni locali selezionate?`)) return;
    this._busy = true; this._render(); let deleted = 0;
    try {
      for (const item of items) {
        await this._hass.callWS({ ...this._message("delete"), recording_id: item.recording_id });
        this._selected.delete(item.recording_id);
        await this._listManager.forget(`local:${item.recording_id}`);
        deleted += 1;
      }
      this._setMessage(`${deleted} registrazioni eliminate.`);
    } catch (_error) { this._setMessage(`Eliminazione interrotta: ${deleted}/${items.length}.`); }
    finally { this._busy = false; await this.reload(); }
  },

  async _backup(item) {
    if (!globalThis.confirm("Copiare e verificare questa registrazione sul backup NFS?")) return;
    this._busy = true; this._render();
    try {
      const result = await backupRecording(this._hass, this._config, item);
      this._setMessage(result.status === "existing" ? `Backup già verificato: ${result.relative_path}`
        : `Backup NFS completato: ${result.relative_path}`);
    } catch (_error) { this._setMessage("Backup non riuscito: mount, spazio o checksum non validi."); }
    finally { this._busy = false; this._render(); }
  },

  async _backupAll() {
    let ready;
    try { ready = await readyRecordings((page, size) => this._fetch(page, size), this._config.alias); }
    catch (_error) { this._setMessage("Archivio non leggibile per il backup."); return; }
    if (!ready.length) { this._setMessage("Nessuna registrazione pronta da copiare."); return; }
    if (!globalThis.confirm(`Copiare e verificare ${ready.length} registrazioni sul backup NFS?`)) return;
    this._busy = true; this._render(); let completed = 0;
    try {
      for (const item of ready) {
        await backupRecording(this._hass, this._config, item); completed += 1;
        this._setMessage(`Backup NFS: ${completed}/${ready.length} verificati…`);
      }
      this._setMessage(`Backup NFS completato: ${completed} registrazioni verificate.`);
    } catch (_error) { this._setMessage(`Backup interrotto: ${completed}/${ready.length} verificati.`); }
    finally { this._busy = false; this._render(); }
  },

  async _download(item) {
    try {
      const path = recordingMediaPath(this._config, item.recording_id);
      const signed = await this._hass.callWS({ type: "auth/sign_path", path, expires: 300 });
      const link = document.createElement("a"); link.href = this._hass.hassUrl(signed.path);
      link.download = `${this._config.provider}-${item.camera}-${item.recording_id}.${
        this._config.provider === "blink" ? "ts" : "mpeg"}`; link.click();
    } catch (_error) { this._setMessage("Download non disponibile."); }
  },

  async _play(item) {
    try { await this.$("player").open(this._hass, this._config, item); }
    catch (_error) { this._setMessage("Riproduzione non disponibile."); }
  },

  async _copyArchivePath() {
    const path = this._storage?.directory; if (!path) return;
    try { await globalThis.navigator.clipboard.writeText(path); this._setMessage("Percorso copiato."); }
    catch (_error) { this._setMessage(`Percorso archivio: ${path}`); }
  },
};
