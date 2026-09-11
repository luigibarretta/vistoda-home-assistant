import { copy } from "./panel-copy.js";
import { backupRecording, readyRecordings } from "./provider-recording-backup.js";
import { recordingMediaPath } from "./provider-recording-model.js";

export const providerRecordingActions = {
  async _start() {
    if (!this._config || this._busy) return;
    const duration = Number(this.$("duration").value);
    if (!globalThis.confirm(copy(this, "Registrare {p0} secondi del live in archivio locale?", { p0: duration }))) return;
    this._busy = true; this._setMessage(copy(this, "Avvio registrazione…")); this._render();
    try {
      await this._hass.callWS({ ...this._message("create"), duration_seconds: duration,
        request_id: globalThis.crypto.randomUUID() });
      this._setMessage(copy(this, "Registrazione di {p0} secondi avviata.", { p0: duration }));
    } catch (_error) {
      this._setMessage(copy(this, "Registrazione non avviata: verifica live, disponibilità e quota."));
    } finally { this._busy = false; await this.reload(); }
  },

  async _delete(item) {
    if (!globalThis.confirm(copy(this, "Eliminare definitivamente questa registrazione locale?"))) return;
    this._busy = true; this._render();
    const mediaId = `local:${item.recording_id}`;
    try {
      await this._hass.callWS({ ...this._message("delete"), recording_id: item.recording_id });
      this._selected.delete(item.recording_id);
      await this._listManager.forget(mediaId);
      this._setMessage(copy(this, "Registrazione eliminata."));
    } catch (_error) {
      this._setMessage(copy(this, "La registrazione non può essere eliminata mentre è attiva."));
    } finally { this._busy = false; await this.reload(); }
  },

  async _deleteSelected() {
    const items = this._items.filter((item) => this._selected.has(item.recording_id)
      && !["pending", "recording"].includes(item.status));
    if (!items.length) return;
    if (!globalThis.confirm(copy(this, "Eliminare definitivamente {p0} registrazioni locali selezionate?", { p0: items.length }))) return;
    this._busy = true; this._render(); let deleted = 0;
    try {
      for (const item of items) {
        await this._hass.callWS({ ...this._message("delete"), recording_id: item.recording_id });
        this._selected.delete(item.recording_id);
        await this._listManager.forget(`local:${item.recording_id}`);
        deleted += 1;
      }
      this._setMessage(copy(this, "{p0} registrazioni eliminate.", { p0: deleted }));
    } catch (_error) { this._setMessage(copy(this, "Eliminazione interrotta: {p0}/{p1}.", { p0: deleted, p1: items.length })); }
    finally { this._busy = false; await this.reload(); }
  },

  async _backup(item) {
    if (!globalThis.confirm(copy(this, "Copiare e verificare questa registrazione sul backup NFS?"))) return;
    this._busy = true; this._render();
    try {
      const result = await backupRecording(this._hass, this._config, item);
      this._setMessage(result.status === "existing" ? copy(this, "Backup già verificato: {p0}", { p0: result.relative_path })
        : copy(this, "Backup NFS completato: {p0}", { p0: result.relative_path }));
    } catch (_error) { this._setMessage(copy(this, "Backup non riuscito: mount, spazio o checksum non validi.")); }
    finally { this._busy = false; this._render(); }
  },

  async _backupAll() {
    let ready;
    try { ready = await readyRecordings((page, size) => this._fetch(page, size), this._config.alias); }
    catch (_error) { this._setMessage(copy(this, "Archivio non leggibile per il backup.")); return; }
    if (!ready.length) { this._setMessage(copy(this, "Nessuna registrazione pronta da copiare.")); return; }
    if (!globalThis.confirm(copy(this, "Copiare e verificare {p0} registrazioni sul backup NFS?", { p0: ready.length }))) return;
    this._busy = true; this._render(); let completed = 0;
    try {
      for (const item of ready) {
        await backupRecording(this._hass, this._config, item); completed += 1;
        this._setMessage(copy(this, "Backup NFS: {p0}/{p1} verificati…", { p0: completed, p1: ready.length }));
      }
      this._setMessage(copy(this, "Backup NFS completato: {p0} registrazioni verificate.", { p0: completed }));
    } catch (_error) { this._setMessage(copy(this, "Backup interrotto: {p0}/{p1} verificati.", { p0: completed, p1: ready.length })); }
    finally { this._busy = false; this._render(); }
  },

  async _download(item) {
    try {
      const path = recordingMediaPath(this._config, item.recording_id);
      const signed = await this._hass.callWS({ type: "auth/sign_path", path, expires: 300 });
      const link = document.createElement("a"); link.href = this._hass.hassUrl(signed.path);
      link.download = `${this._config.provider}-${item.camera}-${item.recording_id}.${
        this._config.provider === "blink" ? "ts" : "mpeg"}`; link.click();
    } catch (_error) { this._setMessage(copy(this, "Download non disponibile.")); }
  },

  async _play(item) {
    try { await this.$("player").open(this._hass, this._config, item); }
    catch (_error) { this._setMessage(copy(this, "Riproduzione non disponibile.")); }
  },

  async _copyArchivePath() {
    const path = this._storage?.directory; if (!path) return;
    try { await globalThis.navigator.clipboard.writeText(path); this._setMessage(copy(this, "Percorso copiato.")); }
    catch (_error) { this._setMessage(copy(this, "Percorso archivio: {p0}", { p0: path })); }
  },
};
