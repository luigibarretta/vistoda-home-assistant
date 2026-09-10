import { BASE_STYLES, MEDIA_STYLES } from "./panel-styles.js";
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
    this._snapshotRequestedAt = null;
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
        <h2>Spioncino EZVIZ</h2><div class="muted">Snapshot e streaming transitano nel
        bridge privato; il browser comunica soltanto con Home Assistant.</div></div>
        <span class="badge off" id="availability">Verifica…</span></section>
      <section class="card media-card" id="camera-card"><div class="stage">
        <div class="placeholder" id="placeholder"><ha-icon icon="mdi:doorbell-video"></ha-icon>
          Snapshot non disponibile</div><div class="loader" id="loader" hidden>
          <ha-icon icon="mdi:loading"></ha-icon><strong>Caricamento snapshot…</strong></div>
          <img id="snapshot" alt="Snapshot spioncino EZVIZ" hidden></div>
        <div class="media-body"><div class="media-title"><div><h3 id="camera-name">Ingresso</h3>
          <div class="muted">VTM cloud privato con remux MPEG-TS condiviso</div>
          <div class="muted" id="snapshot-time"></div></div>
          <span class="badge off" id="camera-state">Non disponibile</span></div>
          <div class="facts"><div class="fact"><ha-icon icon="mdi:lan-connect"></ha-icon>
            <div><span>Connessione</span><strong id="connection">—</strong></div></div>
            <div class="fact"><ha-icon icon="mdi:video-wireless-outline"></ha-icon>
            <div><span>Live</span><strong>Su richiesta</strong></div></div>
            <div class="fact"><ha-icon icon="mdi:camera-outline"></ha-icon>
            <div><span>Snapshot</span><strong id="snapshot-state">Verifica…</strong></div></div></div>
          <div class="actions"><button class="primary" id="live"
            title="Apri il live in Home Assistant"><ha-icon icon="mdi:video-wireless-outline"></ha-icon>
            <span>Apri live</span></button><button id="refresh" title="Ricarica lo snapshot EZVIZ">
            <ha-icon icon="mdi:camera-retake-outline"></ha-icon><span>Aggiorna snapshot</span></button></div>
          <div class="muted" id="message" role="status"></div>
          <vistoda-provider-recordings id="recordings"></vistoda-provider-recordings>
          <div class="notice muted">Questo archivio è standalone e separato da SceneTrove:
            registra soltanto quando lo richiedi qui.</div></div></section>
      <section class="card empty" id="empty" hidden>Nessuna telecamera EZVIZ configurata.</section>`;
    this.$ = (id) => this.shadowRoot.getElementById(id);
    this.$("live").addEventListener("click", () => this._openLive());
    this.$("refresh").addEventListener("click", () => this._refresh());
    this.$("snapshot").addEventListener("error", () => {
      this._imageState = "error";
      this._renderImage();
    });
    this.$("snapshot").addEventListener("load", () => {
      this._imageState = "loaded";
      this._renderImage();
      setText(this.shadowRoot, "message", "Ultimo snapshot salvato disponibile");
    });
  }

  _cameraDevice() { return devicesWithDomain(this._info, "ezviz", "camera")[0] || null; }

  _render() {
    if (!this._mounted) this._mount();
    const provider = this._info?.providers?.ezviz;
    const device = this._cameraDevice();
    const camera = firstEntity(device, "camera");
    const state = entityState(this._hass, camera);
    const connectivity = firstEntity(device, "binary_sensor", (item) => (
      item.device_class === "connectivity"
    ));
    const connectivityState = entityState(this._hass, connectivity);
    this.$("availability").textContent = provider?.available ? "Operativo" : "Non disponibile";
    this.$("availability").classList.toggle("off", !provider?.available);
    this.$("camera-card").hidden = !device;
    this.$("empty").hidden = Boolean(device);
    if (!device) {
      this.$("recordings").configure(this._hass, null);
      return;
    }
    setText(this.shadowRoot, "camera-name", device.name);
    const available = state && state.state !== "unavailable";
    setText(this.shadowRoot, "camera-state", available ? "Disponibile" : "Non disponibile");
    this.$("camera-state").classList.toggle("off", !available);
    setText(this.shadowRoot, "connection", connectivityState?.state === "on"
      ? "Connesso" : connectivityState?.state === "off" ? "Disconnesso" : "Non rilevata");
    setText(this.shadowRoot, "snapshot-time", snapshotTimeText(
      state,
      this._hass?.locale?.language || "it-IT",
      this._snapshotRequestedAt,
    ));
    const entry = provider?.entries?.find((item) => item.alias === state?.attributes?.alias)
      || provider?.entries?.[0];
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
  }

  _openLive() {
    openMoreInfo(this, firstEntity(this._cameraDevice(), "camera")?.entity_id);
  }

  async _refresh() {
    const provider = this._info?.providers?.ezviz;
    const entry = provider?.entries?.[0];
    if (!entry || !this._hass) return;
    setText(this.shadowRoot, "message", "Richiesta di un nuovo snapshot…");
    this.$("refresh").disabled = true;
    try {
      const result = await this._hass.callWS({ type: "media_bridge/ezviz/snapshot/refresh",
        entry_id: entry.entry_id });
      this._snapshotRequestedAt = Date.parse(result.updated_at) || Date.now();
      this._nonce = Date.now(); this._render();
    } catch (_error) {
      setText(this.shadowRoot, "message", "Nuovo snapshot non disponibile.");
    } finally { this.$("refresh").disabled = false; }
  }

  _renderImage() {
    const loading = this._imageState === "loading";
    const loaded = this._imageState === "loaded";
    this.$("loader").hidden = !loading;
    this.$("snapshot").hidden = !loaded;
    this.$("placeholder").hidden = loading || loaded;
    setText(this.shadowRoot, "snapshot-state", loading
      ? "Caricamento…" : loaded ? "Disponibile" : "Non disponibile");
    if (loading) setText(this.shadowRoot, "message", "Caricamento dello snapshot in corso…");
    if (this._imageState === "error") {
      setText(this.shadowRoot, "message", "Snapshot non disponibile; il live può restare operativo.");
    }
  }
}

if (!customElements.get("vistoda-ezviz-view")) {
  customElements.define("vistoda-ezviz-view", VistodaEzvizView);
}
