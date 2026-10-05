import { copy } from "./panel-copy.js";
import { CameraLiveDialog } from "./camera-live-dialog.js";
import { firstEntity, setText } from "./panel-helpers.js";
import { entryPtzTargets } from "./ezviz-ptz-model.js";
import {
  cachedControlSource, controlSourceStale, sourceSignature, writeAllowed,
} from "./ezviz-control-source.js";

const SETTLE_MS = 5000;

export const ezvizViewActions = {
  _openLive() {
    this._liveDialog ||= new CameraLiveDialog(this);
    // PTZ follows the entry's control source: the Vistoda EZVIZ app, or the
    // native buttons of the bound camera when delegated to the official integration.
    // Every press re-checks the live delegation switch against that source.
    const entry = this._cameraEntry();
    const ptzAllowed = this._writeGuard(entry);
    const ptz = ptzAllowed() ? entryPtzTargets(entry, this._hass?.states) : [];
    this._liveDialog.open(this._hass, firstEntity(this._cameraDevice(), "camera")?.entity_id, { ptz, ptzAllowed });
  },

  // A guard bound to the source the snapshot prepared the write for.
  _writeGuard(entry) {
    const target = cachedControlSource(entry);
    return () => writeAllowed(this._cameraEntry(), this._hass?.states, target);
  },

  // Panel info is a snapshot: reload it when a delegation switch flips or its
  // entry reloads, and again shortly after for entities added by the first poll.
  _syncSource() {
    const entries = this._info?.providers?.ezviz?.entries || [];
    const signature = sourceSignature(entries, this._hass?.states);
    const changed = this._sourceSignature !== undefined && signature !== this._sourceSignature;
    this._sourceSignature = signature;
    const stale = entries.some((entry) => controlSourceStale(entry, this._hass?.states));
    if (!changed && !(stale && Date.now() - (this._staleAt || 0) > SETTLE_MS)) return;
    if (stale) this._staleAt = Date.now();
    this._refreshInfo();
    clearTimeout(this._settleTimer);
    this._settleTimer = setTimeout(() => this._refreshInfo(), SETTLE_MS);
  },

  async _refreshInfo() {
    if (this._infoPending || !this._hass) return;
    this._infoPending = true;
    try {
      this._info = await this._hass.callWS({ type: "media_bridge/panel/info" });
      this._render();
    } catch { /* Keep the snapshot: every write stays guarded. */ }
    finally { this._infoPending = false; }
  },

  async _refresh() {
    const entry = this._cameraEntry();
    if (!entry || !this._hass || this._snapshotPending) return;
    const generation = this._cameraGeneration;
    const camera = firstEntity(this._cameraDevice(), "camera");
    const cameraId = camera?.entity_id || "";
    const hass = this._hass;
    this._snapshotPending = true;
    setText(this.shadowRoot, "message", copy(this, "Richiesta di un nuovo snapshot…"));
    this.$("refresh").disabled = true;
    try {
      const result = await hass.callWS({ type: "media_bridge/ezviz/snapshot/refresh",
        entry_id: entry.entry_id });
      if (generation !== this._cameraGeneration || cameraId !== this._selectedCameraId) return;
      this._snapshotTimes.set(cameraId, Date.parse(result.updated_at) || Date.now());
      this._nonce = Date.now(); this._render();
    } catch (_error) {
      if (generation === this._cameraGeneration && cameraId === this._selectedCameraId) {
        setText(this.shadowRoot, "message", copy(this, "Nuovo snapshot non disponibile."));
      }
    } finally {
      if (generation === this._cameraGeneration && cameraId === this._selectedCameraId) {
        this._snapshotPending = false;
        this.$("refresh").disabled = !this._cameraEntry();
      }
    }
  },

  _renderImage() {
    const loading = this._imageState === "loading";
    const loaded = this._imageState === "loaded";
    this.$("loader").hidden = !loading;
    this.$("snapshot").hidden = !loaded;
    this.$("placeholder").hidden = loading || loaded;
    setText(this.shadowRoot, "snapshot-state", loading
      ? copy(this, "Caricamento…") : loaded ? copy(this, "Disponibile") : copy(this, "Non disponibile"));
    if (loading) setText(this.shadowRoot, "message", copy(this, "Caricamento dello snapshot in corso…"));
    if (this._imageState === "error") {
      setText(this.shadowRoot, "message", copy(this, "Snapshot non disponibile; il live può restare operativo."));
    }
  },
};
