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
  #stage:is(:fullscreen, :-webkit-full-screen) { width:100vw; height:100vh;
    max-height:none; aspect-ratio:auto; border-radius:0; background:#000; }
  #stage:is(:fullscreen, :-webkit-full-screen) #legacy-live {
    display:flex; align-items:center; justify-content:center; }
  #stage:is(:fullscreen, :-webkit-full-screen) .blink-legacy-card {
    width:min(100vw, calc(100vh * var(--live-aspect, 1.777778))); height:auto; }
  #fullscreen { position:absolute; top:max(8px, env(safe-area-inset-top));
    right:max(8px, env(safe-area-inset-right)); z-index:5; width:44px; height:44px;
    padding:8px; min-width:44px; background:#181818; color:#fff; }
</style>
<section class="provider-head" id="provider-head"><div><div class="eyebrow">Vistoda · Blink</div>
  <h2 data-i18n="blinkTitle">Telecamere Blink</h2><div class="muted" data-i18n="blinkIntro">Gli snapshot esistenti non risvegliano
  le camere. Aggiornamento e live partono soltanto su richiesta.</div></div>
  <span class="badge off" id="availability"><span data-copy="Verifica…">Verifica…</span></span></section>
<section class="card empty" id="empty" hidden><p data-i18n="noCameras">Nessuna telecamera Blink configurata.</p>
  <a class="button primary" href="/config/integrations/dashboard" data-i18n="configureProvider">Configura Blink</a></section>
<section class="card system" id="system"><div><strong id="system-name"><span data-copy="Sistema Blink">Sistema Blink</span></strong>
  <div class="muted" id="system-state"><span data-copy="Stato non disponibile">Stato non disponibile</span></div></div>
  <div class="actions"><button id="disarm"><ha-icon icon="mdi:shield-off-outline"></ha-icon>
    <span data-i18n="disarm">Disarma</span></button><button class="primary" id="arm">
    <ha-icon icon="mdi:shield-lock-outline"></ha-icon><span data-i18n="arm">Arma</span></button></div></section>
<section class="card media-card" id="gallery">
  <div class="stage" id="stage"><div class="placeholder" id="placeholder"><ha-icon
    icon="mdi:cctv"></ha-icon><span data-i18n="noSnapshot">Snapshot non disponibile</span></div><img id="snapshot" alt="">
    <video id="live-video" autoplay playsinline muted hidden></video>
    <div id="legacy-live" hidden></div>
    <button id="fullscreen" hidden aria-label="Schermo intero" title="Schermo intero"
      data-copy-aria-label="Schermo intero" data-copy-title="Schermo intero" aria-pressed="false">
      <ha-icon icon="mdi:fullscreen"></ha-icon></button></div>
  <div class="media-body"><div class="media-title"><div><h3 id="camera-name"><span data-copy="Telecamera">Telecamera</span></h3>
    <div class="muted" id="camera-position"></div><div class="muted" id="snapshot-time"></div>
    </div><span class="badge off" id="camera-state"><span data-copy="Non disponibile">Non disponibile</span></span></div>
    <div class="facts"><div class="fact"><ha-icon id="battery-icon" icon="mdi:battery"></ha-icon>
      <div><span data-i18n="battery"><span data-copy="Batteria">Batteria</span></span><strong id="battery">—</strong></div></div>
      <div class="fact"><ha-icon icon="mdi:thermometer"></ha-icon><div><span data-i18n="temperature"><span data-copy="Temperatura">Temperatura</span></span>
      <strong id="temperature">—</strong></div></div>
      <div class="fact"><ha-icon icon="mdi:video-box"></ha-icon><div><span data-i18n="recentClips">Clip recenti</span>
      <strong id="clips">0</strong></div></div></div>
    <div class="actions"><button class="primary" id="live" title="Apri il live in Home Assistant" data-i18n-title="openLive">
      <ha-icon icon="mdi:video-wireless-outline"></ha-icon><span><span data-copy="Apri live">Apri live</span></span></button>
      <button id="refresh" title="Richiedi un nuovo snapshot alla telecamera" data-i18n-title="refreshSnapshot">
      <ha-icon icon="mdi:camera-retake-outline"></ha-icon><span data-i18n="refreshSnapshot">Aggiorna snapshot</span></button>
      <button id="motion"><ha-icon id="motion-icon" icon="mdi:motion-sensor"></ha-icon>
      <span id="motion-label"><span data-copy="Movimento">Movimento</span></span></button><button id="details">
      <ha-icon icon="mdi:cog-outline"></ha-icon><span data-i18n="detailsSettings">Dettagli e impostazioni</span></button>
      <button id="speaker" hidden><ha-icon id="speaker-icon" icon="mdi:volume-off"></ha-icon>
      <span id="speaker-label"><span data-copy="Attiva audio">Attiva audio</span></span></button><button id="microphone" hidden aria-describedby="microphone-unavailable">
      <ha-icon id="microphone-icon" icon="mdi:microphone-off"></ha-icon>
      <span id="microphone-label"><span data-copy="Attiva microfono">Attiva microfono</span></span></button></div>
    <p class="muted" id="microphone-unavailable" hidden data-copy="Questo live non supporta ancora l’invio della voce alla telecamera da Vistoda.">Questo live non supporta ancora l’invio della voce alla telecamera da Vistoda.</p>
    <div class="muted" id="message" role="status"></div>
    <vistoda-provider-recordings id="recordings"></vistoda-provider-recordings></div>
</section>
<nav class="pager" id="pager" aria-label="Seleziona telecamera" data-i18n-aria-label="cameraSelect"><button data-i18n-aria-label="cameraPrevious" id="previous"
  aria-label="Telecamera precedente"><ha-icon icon="mdi:chevron-left"></ha-icon></button>
  <div class="dots" id="dots"></div><button data-i18n-aria-label="cameraNext" id="next" aria-label="Telecamera successiva">
  <ha-icon icon="mdi:chevron-right"></ha-icon></button></nav>
<vistoda-blink-storage id="storage"></vistoda-blink-storage>
<section id="details-page" hidden><div class="detail-head"><button id="details-back"
  title="Torna alle telecamere" data-copy-title="Torna alle telecamere"><ha-icon icon="mdi:arrow-left"></ha-icon>
  <span><span data-copy="Telecamere">Telecamere</span></span></button><div><div class="eyebrow"><span data-copy="Dettaglio camera">Dettaglio camera</span></div>
  <h2 id="details-title"><span data-copy="Impostazioni">Impostazioni</span></h2></div></div>
  <vistoda-blink-settings id="settings"><vistoda-blink-zones id="zones" slot="zones"
    embedded></vistoda-blink-zones></vistoda-blink-settings></section>`;
