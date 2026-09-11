import { copy, localizeCopy } from "./panel-copy.js";
import { BASE_STYLES, MEDIA_STYLES } from "./panel-styles.js";
import { localize, localizeElements } from "./panel-localize.js";
import { ezvizViewNavigation } from "./ezviz-view-navigation.js";
import "./provider-recordings.js";
import {
  devicesWithDomain,
  entityState,
  firstEntity,
  openMoreInfo,
  pictureUrl,
  setText,
  snapshotTimeText,
} from "./panel-helpers.js";

class VistodaEzvizView extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._mounted = false;
    this._info = null;
    this._nonce = 0;
    this._imageUrl = "";
    this._imageState = "empty";
    this._snapshotTimes = new Map();
    this._cameraIndex = 0;
    this._selectedCameraId = "";
    this._cameraGeneration = 0;
    this._swipeStart = null;
  }

  set hass(value) { this._hass = value; this._render(); }
  set info(value) { this._info = value; this._render(); }

  _mount() {
    this._mounted = true;
    this.shadowRoot.innerHTML = `
      <style>${BASE_STYLES}${MEDIA_STYLES}
        .notice { margin-top:16px; padding:14px; border-radius:14px;
          background:color-mix(in srgb,var(--primary-color) 10%,transparent); }
        .loader { position:absolute; inset:0; z-index:2; display:grid; place-content:center;
          gap:10px; text-align:center; color:#fff; background:#111c; backdrop-filter:blur(2px); }
        .loader[hidden] { display:none !important; }
        .loader ha-icon { --mdc-icon-size:42px; margin:auto; animation:spin 1s linear infinite; }
        @keyframes spin { to { transform:rotate(360deg); } }
        #message { min-height:21px; margin-top:12px; }
      </style>
      <section class="provider-head"><div><div class="eyebrow">Vistoda · EZVIZ</div>
        <h2 data-i18n="ezvizTitle">Telecamere EZVIZ</h2><div class="muted" data-i18n="ezvizIntro">Consulta l’ultima immagine salvata.
        Live e nuove immagini partono quando li richiedi.</div></div>
        <span class="badge off" id="availability"><span data-copy="Verifica…">Verifica…</span></span></section>
      <section class="card media-card" id="camera-card"><div class="stage" id="stage">
        <div class="placeholder" id="placeholder"><ha-icon icon="mdi:doorbell-video"></ha-icon>
          <span data-i18n="noSnapshot">Snapshot non disponibile</span></div><div class="loader" id="loader" hidden>
          <ha-icon icon="mdi:loading"></ha-icon><strong data-i18n="snapshotLoading">Caricamento snapshot…</strong></div>
          <img id="snapshot" alt="Snapshot spioncino EZVIZ" data-copy-alt="Snapshot spioncino EZVIZ" hidden></div>
        <div class="media-body"><div class="media-title"><div><h3 id="camera-name"><span data-copy="Ingresso">Ingresso</span></h3>
          <div class="muted" id="camera-position"></div>
          <div class="muted" data-i18n="savedImage">Ultima immagine salvata in Home Assistant</div>
          <div class="muted" id="snapshot-time"></div></div>
          <span class="badge off" id="camera-state"><span data-copy="Non disponibile">Non disponibile</span></span></div>
          <div class="facts"><div class="fact"><ha-icon icon="mdi:lan-connect"></ha-icon>
            <div><span data-i18n="connection">Connessione</span><strong id="connection">—</strong></div></div>
            <div class="fact"><ha-icon icon="mdi:video-wireless-outline"></ha-icon>
            <div><span>Live</span><strong data-i18n="onRequest">Su richiesta</strong></div></div>
            <div class="fact"><ha-icon icon="mdi:camera-outline"></ha-icon>
            <div><span>Snapshot</span><strong id="snapshot-state"><span data-copy="Verifica…">Verifica…</span></strong></div></div></div>
          <div class="actions"><button class="primary" id="live"
            title="Apri il live in Home Assistant" data-i18n-title="openLive"><ha-icon icon="mdi:video-wireless-outline"></ha-icon>
            <span data-i18n="openLive"><span data-copy="Apri live">Apri live</span></span></button><button id="refresh" title="Ricarica lo snapshot EZVIZ" data-i18n-title="refreshSnapshot">
            <ha-icon icon="mdi:camera-retake-outline"></ha-icon><span data-i18n="refreshSnapshot">Aggiorna snapshot</span></button></div>
          <div class="muted" id="message" role="status"></div>
          <vistoda-provider-recordings id="recordings"></vistoda-provider-recordings>
          <div class="notice muted"><span data-copy="Questo archivio è standalone e separato da SceneTrove: registra soltanto quando lo richiedi qui.">Questo archivio è standalone e separato da SceneTrove:
            registra soltanto quando lo richiedi qui.</span></div></div></section>
      <nav class="pager" id="pager" aria-label="Seleziona telecamera" data-i18n-aria-label="cameraSelect">
        <button data-i18n-aria-label="cameraPrevious" id="previous" aria-label="Telecamera precedente">
          <ha-icon icon="mdi:chevron-left"></ha-icon></button><div class="dots" id="dots"></div>
        <button data-i18n-aria-label="cameraNext" id="next" aria-label="Telecamera successiva">
          <ha-icon icon="mdi:chevron-right"></ha-icon></button></nav>
      <section class="card empty" id="empty" hidden><p data-i18n="noCameras">Nessuna telecamera EZVIZ configurata.</p>
        <a class="button primary" href="/config/integrations/dashboard" data-i18n="configureProvider">Configura EZVIZ</a></section>`; localizeCopy(this.shadowRoot, this);
    this.$ = (id) => this.shadowRoot.getElementById(id);
    this.$("previous").addEventListener("click", () => this._move(-1));
    this.$("next").addEventListener("click", () => this._move(1));
    this.$("stage").addEventListener("pointerdown", (event) => this._startSwipe(event));
    this.$("stage").addEventListener("pointerup", (event) => this._finishSwipe(event));
    this.$("stage").addEventListener("pointercancel", () => { this._swipeStart = null; });
    this.$("live").addEventListener("click", () => this._openLive());
    this.$("refresh").addEventListener("click", () => this._refresh());
    this.$("snapshot").addEventListener("error", () => {
      this._imageState = "error";
      this._renderImage();
    });
    this.$("snapshot").addEventListener("load", () => {
      this._imageState = "loaded";
      this._renderImage();
      setText(this.shadowRoot, "message", copy(this, "Ultimo snapshot salvato disponibile"));
    });
  }

  _cameraDevice() { return devicesWithDomain(this._info, "ezviz", "camera")[this._cameraIndex] || null; }

  _cameraEntry() {
    const entries = this._info?.providers?.ezviz?.entries || [];
    const camera = firstEntity(this._cameraDevice(), "camera");
    const state = entityState(this._hass, camera);
    const entryId = camera?.config_entry_id || state?.attributes?.entry_id;
    const alias = state?.attributes?.alias;
    if (entryId) {
      const exact = entries.find((entry) => entry.entry_id === entryId);
      return exact && (!alias || !exact.alias || exact.alias === alias) ? exact : null;
    }
    const matching = entries.filter((entry) => entry.alias && entry.alias === alias);
    if (matching.length === 1) return matching[0];
    return entries.length === 1 && devicesWithDomain(this._info, "ezviz", "camera").length === 1
      ? entries[0] : null;
  }

  _render() {
    if (!this._mounted) this._mount();
    localizeCopy(this.shadowRoot, this);
    localizeElements(this.shadowRoot, this._hass, { provider: "EZVIZ" });
    const cameras = devicesWithDomain(this._info, "ezviz", "camera");
    this._reconcileCameraSelection(cameras);
    const provider = this._info?.providers?.ezviz;
    const device = this._cameraDevice();
    const camera = firstEntity(device, "camera");
    const state = entityState(this._hass, camera);
    const connectivity = firstEntity(device, "binary_sensor", (item) => (
      item.device_class === "connectivity"
    ));
    const connectivityState = entityState(this._hass, connectivity);
    const entry = this._cameraEntry();
    const providerAvailable = entry?.available ?? provider?.available;
    this.$("availability").textContent = localize(this._hass, providerAvailable ? "ready" : "unavailable");
    this.$("availability").classList.toggle("off", !providerAvailable);
    this.$("camera-card").hidden = !device;
    this.$("pager").hidden = !device;
    this.$("empty").hidden = Boolean(device);
    if (!device) {
      this.$("recordings").configure(this._hass, null);
      return;
    }
    setText(this.shadowRoot, "camera-name", device.name);
    setText(this.shadowRoot, "camera-position", copy(this, "{p0} di {p1}", {
      p0: this._cameraIndex + 1, p1: cameras.length,
    }));
    const available = state && state.state !== "unavailable";
    setText(this.shadowRoot, "camera-state", available ? copy(this, "Disponibile") : copy(this, "Non disponibile"));
    this.$("camera-state").classList.toggle("off", !available);
    setText(this.shadowRoot, "connection", connectivityState?.state === "on"
      ? copy(this, "Connesso") : connectivityState?.state === "off" ? copy(this, "Disconnesso") : copy(this, "Non rilevata"));
    setText(this.shadowRoot, "snapshot-time", snapshotTimeText(
      state,
      this._hass?.locale?.language || "it-IT",
      this._snapshotTimes.get(camera?.entity_id),
    ));
    this.$("refresh").disabled = !entry || this._snapshotPending;
    this.$("recordings").configure(this._hass, entry ? {
      provider: "ezviz", entryId: entry.entry_id, alias: entry.alias,
    } : null);
    const url = pictureUrl(this._hass, camera, this._nonce);
    if (url && this._imageUrl !== url) {
      this._imageUrl = url;
      this._imageState = "loading";
      this.$("snapshot").src = url;
    } else if (!url) {
      this._imageUrl = "";
      this._imageState = "empty";
    }
    this._renderImage();
    this.$("live").disabled = !available;
    this.$("previous").disabled = cameras.length < 2;
    this.$("next").disabled = cameras.length < 2;
    this._renderDots(cameras);
  }

  _openLive() {
    openMoreInfo(this, firstEntity(this._cameraDevice(), "camera")?.entity_id);
  }

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
  }

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
  }
}

Object.assign(VistodaEzvizView.prototype, ezvizViewNavigation);
if (!customElements.get("vistoda-ezviz-view")) {
  customElements.define("vistoda-ezviz-view", VistodaEzvizView);
}
