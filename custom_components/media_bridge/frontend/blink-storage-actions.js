import { copy } from "./panel-copy.js";
export const blinkStorageActions = {
  _path(storage, clip) {
    return `/api/blink_live_bridge/v1/local-storage/${storage.network_id}/` +
      `${storage.sync_module_id}/${storage.manifest_id}/${clip.id}/media`;
  },

  async _signedPath(storage, clip) {
    const signed = await this._hass.callWS({ type: "auth/sign_path",
      path: this._path(storage, clip), expires: 900 });
    return this._hass.hassUrl(signed.path);
  },

  async _play(storage, clip) {
    try {
      this._closePlayer(); this.$("player-title").textContent =
        `${clip.device_name || copy(this, "Telecamera Blink")} · ${this._date(clip.created_at)}`;
      this.$("video").src = await this._signedPath(storage, clip);
      this.$("player").hidden = false; this.$("video").load();
      this.$("player").scrollIntoView({ behavior: "smooth", block: "nearest" });
    } catch (_error) { this._setMessage(copy(this, "Riproduzione clip non disponibile.")); }
  },

  _closePlayer() {
    const video = this.$("video"); video.pause(); video.removeAttribute("src"); video.load();
    this.$("player").hidden = true;
  },

  async _download(storage, clip) {
    try {
      const link = document.createElement("a"); link.href = await this._signedPath(storage, clip);
      link.download = `blink-usb-${clip.device_name || "camera"}-${clip.id}.mp4`; link.click();
    } catch (_error) { this._setMessage(copy(this, "Download clip non disponibile.")); }
  },

  _backupMessage(storage, clip) {
    return { type: "media_bridge/blink/usb/backup", network_id: Number(storage.network_id),
      sync_module_id: Number(storage.sync_module_id), manifest_id: Number(storage.manifest_id),
      clip_id: Number(clip.id), camera: this._safeCamera(clip.device_name),
      created_at: String(clip.created_at || ""), clip_length_ms: clip.clip_length_ms ?? null };
  },

  async _backupSingle(storage, clip) {
    try { await this._backup(storage, clip); }
    catch (_error) { this._setMessage(copy(this, "Backup NFS Blink non riuscito.")); }
  },

  async _backup(storage, clip, confirmed = false) {
    if (!confirmed && !globalThis.confirm(copy(this, "Copiare e verificare questa clip Blink sul backup NFS?"))) return;
    const result = await this._hass.callWS(this._backupMessage(storage, clip));
    this._setMessage(result.status === "existing" ? copy(this, "Backup già verificato: {p0}", { p0: result.relative_path })
      : copy(this, "Backup NFS completato: {p0}", { p0: result.relative_path }));
  },

  async _backupAll() {
    if (!this._hass || this._busy) return;
    this._busy = true; this._render();
    try {
      const first = await this._fetch(1, 50); const storages = first.storages || [];
      const total = storages.reduce((sum, item) => sum + (item.pagination?.total_items || 0), 0);
      if (!total) { this._setMessage(copy(this, "Nessuna clip Blink da copiare.")); return; }
      if (!globalThis.confirm(copy(this, "Copiare e verificare {p0} clip Blink sul backup NFS?", { p0: total }))) return;
      const pages = Math.max(1, ...storages.map((item) => item.pagination?.total_pages || 1));
      let completed = 0;
      for (let page = 1; page <= pages; page += 1) {
        const batch = page === 1 ? first : await this._fetch(page, 50);
        for (const storage of batch.storages || []) {
          for (const clip of (storage.clips || []).filter((item) => item.media_available)) {
            await this._backup(storage, clip, true); completed += 1;
            this._setMessage(copy(this, "Backup NFS Blink: {p0}/{p1} verificati…", { p0: completed, p1: total }));
          }
        }
      }
      this._setMessage(copy(this, "Backup NFS Blink completato: {p0} clip verificate.", { p0: completed }));
    } catch (_error) { this._setMessage(copy(this, "Backup NFS Blink interrotto.")); }
    finally { this._busy = false; this._render(); }
  },

  _deleteMessage(storage, clip) {
    return { type: "blink_live_bridge/local_storage/delete", network_id: Number(storage.network_id),
      sync_module_id: Number(storage.sync_module_id), manifest_id: Number(storage.manifest_id),
      clip_id: Number(clip.id) };
  },

  async _deleteOne(storage, clip) {
    const label = `${clip.device_name || copy(this, "Telecamera Blink")} · ${this._date(clip.created_at)}`;
    if (!globalThis.confirm(copy(this, "Eliminare definitivamente la clip “{p0}” dalla chiavetta Blink?", { p0: label }))) return;
    this._busy = true; this._render();
    try {
      await this._hass.callWS(this._deleteMessage(storage, clip));
      this._selected.delete(this._selectionKey(storage, clip));
      await this._listManager.forget(this._mediaId(storage, clip));
      this._setMessage(copy(this, "Clip eliminata."));
    } catch (_error) { this._setMessage(copy(this, "Eliminazione non riuscita: l’indice Blink potrebbe essere cambiato.")); }
    finally { this._busy = false; await this.reload(); }
  },

  async _deleteSelected() {
    const selected = [];
    for (const storage of this._storages) for (const clip of storage.clips || []) {
      if (this._selected.has(this._selectionKey(storage, clip))) selected.push([storage, clip]);
    }
    if (!selected.length) return;
    if (!globalThis.confirm(copy(this, "Eliminare definitivamente {p0} clip selezionate dalla chiavetta Blink?", { p0: selected.length }))) return;
    this._busy = true; this._render(); let deleted = 0;
    try {
      for (const [storage, clip] of selected) {
        await this._hass.callWS(this._deleteMessage(storage, clip));
        this._selected.delete(this._selectionKey(storage, clip));
        await this._listManager.forget(this._mediaId(storage, clip)); deleted += 1;
      }
      this._setMessage(copy(this, "{p0} clip eliminate.", { p0: deleted }));
    } catch (_error) { this._setMessage(copy(this, "Eliminazione interrotta: {p0}/{p1}.", { p0: deleted, p1: selected.length })); }
    finally { this._busy = false; await this.reload(); }
  },

  _openFormat(storage) {
    this._formatStorage = storage;
    this._formatPhrase = `FORMATTA ${storage.network_id}/${storage.sync_module_id}`;
    this.$("format-target").textContent = `${storage.network_name || copy(this, "Sistema Blink")} · Sync Module ${storage.sync_module_id}`;
    this.$("format-phrase").textContent = this._formatPhrase;
    this.$("format-confirmation").value = ""; this.$("confirm-format").disabled = true;
    this.$("format-dialog").showModal(); this.$("format-confirmation").focus();
  },

  async _format() {
    const storage = this._formatStorage; const confirmation = this._formatPhrase;
    if (!storage || this.$("format-confirmation").value !== confirmation) return;
    this._busy = true; this._render(); this._setMessage(copy(this, "Formattazione Blink in corso…"));
    try {
      await this._hass.callWS({ type: "blink_live_bridge/local_storage/format",
        network_id: Number(storage.network_id), sync_module_id: Number(storage.sync_module_id),
        confirmation });
      this._selected.clear(); this._setMessage(copy(this, "Chiavetta formattata dal Sync Module Blink."));
    } catch (_error) { this._setMessage(copy(this, "Formattazione non riuscita o non consentita dal supporto.")); }
    finally { this._busy = false; await this.reload(); }
  },
};
