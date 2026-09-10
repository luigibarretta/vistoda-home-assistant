import { BASE_STYLES, MEDIA_STYLES } from "./panel-styles.js";

export const BLINK_VIEW_TEMPLATE = `<style>${BASE_STYLES}${MEDIA_STYLES}
  #message { min-height:21px; margin-top:12px; }
  .detail-head { display:flex; align-items:center; gap:12px; margin-bottom:16px; }
  .detail-head h2 { margin:0; font-size:23px; }
  .detail-head button { flex:0 0 auto; }
  #live-video { width:100%; height:100%; position:absolute; inset:0; object-fit:contain;
    background:#000; }
  #legacy-live { position:absolute; inset:0; width:100%; height:100%; background:#000; }
  #legacy-live .blink-legacy-card { display:block; width:100%; height:100%; }
</style>
<section class="provider-head" id="provider-head"><div><div class="eyebrow">Vistoda · Blink</div>
  <h2>Telecamere Blink</h2><div class="muted">Gli snapshot esistenti non risvegliano
  le camere. Aggiornamento e live partono soltanto su richiesta.</div></div>
  <span class="badge off" id="availability">Verifica…</span></section>
<section class="card system" id="system"><div><strong id="system-name">Sistema Blink</strong>
  <div class="muted" id="system-state">Stato non disponibile</div></div>
  <div class="actions"><button id="disarm"><ha-icon icon="mdi:shield-off-outline"></ha-icon>
    <span>Disarma</span></button><button class="primary" id="arm">
    <ha-icon icon="mdi:shield-lock-outline"></ha-icon><span>Arma</span></button></div></section>
<section class="card media-card" id="gallery">
  <div class="stage" id="stage"><div class="placeholder" id="placeholder"><ha-icon
    icon="mdi:cctv"></ha-icon>Snapshot non disponibile</div><img id="snapshot" alt="">
    <video id="live-video" autoplay playsinline muted hidden></video>
    <div id="legacy-live" hidden></div></div>
  <div class="media-body"><div class="media-title"><div><h3 id="camera-name">Telecamera</h3>
    <div class="muted" id="camera-position"></div><div class="muted" id="snapshot-time"></div>
    </div><span class="badge off" id="camera-state">Non disponibile</span></div>
    <div class="facts"><div class="fact"><ha-icon id="battery-icon" icon="mdi:battery"></ha-icon>
      <div><span>Batteria</span><strong id="battery">—</strong></div></div>
      <div class="fact"><ha-icon icon="mdi:thermometer"></ha-icon><div><span>Temperatura</span>
      <strong id="temperature">—</strong></div></div>
      <div class="fact"><ha-icon icon="mdi:video-box"></ha-icon><div><span>Clip recenti</span>
      <strong id="clips">0</strong></div></div></div>
    <div class="actions"><button class="primary" id="live" title="Apri il live in Home Assistant">
      <ha-icon icon="mdi:video-wireless-outline"></ha-icon><span>Apri live</span></button>
      <button id="refresh" title="Richiedi un nuovo snapshot alla telecamera">
      <ha-icon icon="mdi:camera-retake-outline"></ha-icon><span>Aggiorna snapshot</span></button>
      <button id="motion"><ha-icon id="motion-icon" icon="mdi:motion-sensor"></ha-icon>
      <span id="motion-label">Movimento</span></button><button id="details">
      <ha-icon icon="mdi:cog-outline"></ha-icon><span>Dettagli e impostazioni</span></button>
      <button id="speaker" hidden><ha-icon id="speaker-icon" icon="mdi:volume-off"></ha-icon>
      <span id="speaker-label">Attiva audio</span></button><button id="microphone" hidden>
      <ha-icon id="microphone-icon" icon="mdi:microphone-off"></ha-icon>
      <span id="microphone-label">Attiva microfono</span></button></div>
    <div class="muted" id="message" role="status"></div>
    <vistoda-provider-recordings id="recordings"></vistoda-provider-recordings></div>
</section>
<nav class="pager" id="pager" aria-label="Seleziona telecamera"><button id="previous"
  aria-label="Telecamera precedente"><ha-icon icon="mdi:chevron-left"></ha-icon></button>
  <div class="dots" id="dots"></div><button id="next" aria-label="Telecamera successiva">
  <ha-icon icon="mdi:chevron-right"></ha-icon></button></nav>
<vistoda-blink-storage id="storage"></vistoda-blink-storage>
<section id="details-page" hidden><div class="detail-head"><button id="details-back"
  title="Torna alle telecamere"><ha-icon icon="mdi:arrow-left"></ha-icon>
  <span>Telecamere</span></button><div><div class="eyebrow">Dettaglio camera</div>
  <h2 id="details-title">Impostazioni</h2></div></div>
  <vistoda-blink-settings id="settings"><vistoda-blink-zones id="zones" slot="zones"
    embedded></vistoda-blink-zones></vistoda-blink-settings></section>`;
