import { BASE_STYLES, MEDIA_STYLES } from "./panel-styles.js";

export const BLINK_VIEW_TEMPLATE = `<style>${BASE_STYLES}${MEDIA_STYLES}
  #message { min-height:21px; margin-top:12px; }
  .detail-head { display:flex; align-items:center; gap:12px; margin-bottom:16px; }
  .detail-head h2 { margin:0; font-size:23px; }
  .detail-head button { flex:0 0 auto; }
</style>
<section class="provider-head" id="provider-head"><div><div class="eyebrow">Vistoda · Blink</div>
  <h2>Telecamere Blink</h2><div class="muted">Gli snapshot esistenti non risvegliano
  le camere. Aggiornamento e live partono soltanto su richiesta.</div></div>
  <span class="badge off" id="availability">Verifica…</span></section>
<section class="card system" id="system"><div><strong id="system-name">Sistema Blink</strong>
  <div class="muted" id="system-state">Stato non disponibile</div></div>
  <div class="actions"><button id="disarm">Disarma</button>
    <button class="primary" id="arm">Arma</button></div></section>
<section class="card media-card" id="gallery">
  <div class="stage" id="stage"><div class="placeholder" id="placeholder"><ha-icon
    icon="mdi:cctv"></ha-icon>Snapshot non disponibile</div><img id="snapshot" alt=""></div>
  <div class="media-body"><div class="media-title"><div><h3 id="camera-name">Telecamera</h3>
    <div class="muted" id="camera-position"></div><div class="muted" id="snapshot-time"></div>
    </div><span class="badge off" id="camera-state">Non disponibile</span></div>
    <div class="facts"><div class="fact"><span>Batteria</span><strong id="battery">—</strong></div>
      <div class="fact"><span>Temperatura</span><strong id="temperature">—</strong></div>
      <div class="fact"><span>Clip recenti</span><strong id="clips">0</strong></div></div>
    <div class="actions"><button class="primary" id="live" title="Apri il live in Home Assistant">Apri live</button>
      <button id="refresh" title="Richiedi un nuovo snapshot alla telecamera">Aggiorna snapshot</button>
      <button id="motion">Movimento</button><button id="details">Dettagli e impostazioni</button></div>
    <div class="muted" id="message" role="status"></div>
    <vistoda-provider-recordings id="recordings"></vistoda-provider-recordings></div>
</section>
<nav class="pager" id="pager" aria-label="Seleziona telecamera"><button id="previous"
  aria-label="Telecamera precedente" title="Telecamera precedente"
  data-tooltip="Mostra la telecamera precedente">←</button><div class="dots" id="dots"></div>
  <button id="next" aria-label="Telecamera successiva" title="Telecamera successiva"
  data-tooltip="Mostra la telecamera successiva">→</button></nav>
<section id="details-page" hidden><div class="detail-head"><button id="details-back"
  title="Torna alle telecamere">← Telecamere</button><div><div class="eyebrow">Dettaglio camera</div>
  <h2 id="details-title">Impostazioni</h2></div></div>
  <vistoda-blink-settings id="settings"></vistoda-blink-settings>
  <vistoda-blink-zones id="zones"></vistoda-blink-zones></section>`;
