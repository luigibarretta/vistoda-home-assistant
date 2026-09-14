import { copy } from "./panel-copy.js";
import { CameraLiveDialog } from "./camera-live-dialog.js";
import { firstEntity, setText } from "./panel-helpers.js";

export const ezvizViewActions = {
  _openLive() {
    this._liveDialog ||= new CameraLiveDialog(this);
    this._liveDialog.open(this._hass, firstEntity(this._cameraDevice(), "camera")?.entity_id);
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
