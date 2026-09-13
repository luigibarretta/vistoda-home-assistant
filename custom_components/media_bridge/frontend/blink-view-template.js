import { BASE_STYLES, MEDIA_STYLES } from "./panel-styles.js";

export const BLINK_VIEW_TEMPLATE = `<style>${BASE_STYLES}${MEDIA_STYLES}
  #message { min-height:21px; margin-top:12px; }
  #system { display:block; }
  #system-controls { display:flex; align-items:center; justify-content:space-between; gap:12px; flex-wrap:wrap; }
  #provider-head { margin-bottom:16px; }
  #live-message { position:absolute; left:8px; right:8px; top:8px; max-width:calc(100% - 68px);
    z-index:4; color:#fff; background:#181818e8; padding:6px 10px; border-radius:8px; font-size:13px; }
  #continue { position:absolute; left:50%; top:50%; transform:translate(-50%,-50%); z-index:6; }
  #microphone { touch-action:none; user-select:none; -webkit-user-select:none;
    flex:0 1 auto; min-width:108px; width:auto; max-width:calc(100% - 104px);
    min-height:44px; height:auto; border:2px solid #fff; border-radius:24px; gap:8px; padding:8px 14px; }
  #microphone ha-icon { --mdc-icon-size:24px; flex-shrink:0; }
  #microphone span { position:static; width:auto; height:auto; margin:0; overflow:visible;
    clip-path:none; white-space:normal; line-height:1.2; font-size:13px; }
  #microphone[aria-pressed="true"] { box-shadow:0 0 0 4px #00bcd466; }
  #talk-status { position:absolute; bottom:88px; left:12px; right:12px; z-index:5;
    text-align:center; color:#fff; background:#181818e8; border-radius:12px; padding:10px;
    pointer-events:none; }
  #live-loader { position:absolute; inset:0; z-index:3; display:grid; place-items:center; background:#000; }
  #live-loader::after { content:""; width:40px; height:40px; border:4px solid #ffffff40;
    border-top-color:#fff; border-radius:50%; animation:live-spin 1s linear infinite; }
  @keyframes live-spin { to { transform:rotate(360deg); } }
  @media (prefers-reduced-motion:reduce) { #live-loader::after { animation:none; } }
  #mobile-live-dialog { border:0; padding:0; margin:0; width:100vw; max-width:none;
    height:100dvh; max-height:none; background:#000; color:#fff; }
  #mobile-live-dialog::backdrop { background:#000; }
  #mobile-stage-slot { height:100%; }
  #mobile-live-dialog #stage { width:100%; height:100%; max-height:none; aspect-ratio:auto; border-radius:0; }
  #mobile-live-dialog #legacy-live { display:flex; align-items:center; justify-content:center; }
  #mobile-live-dialog .blink-legacy-card { width:100%; height:auto; }
  #mobile-live-dialog .stage-actions { bottom:max(16px, env(safe-area-inset-bottom)); }
  #recording-section { margin-top:12px; }
  #recording-section > summary { padding:12px 0; cursor:pointer; font-weight:600; }
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
  #rotate { position:absolute; right:8px; top:64px; z-index:5;
    width:44px; height:44px; min-width:44px; padding:8px; background:#181818; color:#fff; }
  #record-live { position:absolute; right:60px; top:64px; z-index:5;
    width:44px; height:44px; min-width:44px; padding:8px; background:#181818; color:#fff; }
</style>
<section class="card system" id="system"><div class="provider-head" id="provider-head"><div><div class="eyebrow">Vistoda · Blink</div>
  <h2 data-i18n="blinkTitle">Telecamere Blink</h2><div class="muted" data-i18n="blinkIntro">Gli snapshot esistenti non risvegliano
  le camere. Aggiornamento e live partono soltanto su richiesta.</div></div>
  <span class="badge off" id="availability"><span data-copy="Verifica…">Verifica…</span></span></div>
<vistoda-system-arm-control id="system-controls"></vistoda-system-arm-control></section>
<section class="card empty" id="empty" hidden><p data-i18n="noCameras">Nessuna telecamera Blink configurata.</p>
  <a class="button primary" href="/config/integrations/dashboard" data-i18n="configureProvider">Configura Blink</a></section>
<section class="card media-card" id="gallery">
  <div class="stage" id="stage"><div class="placeholder" id="placeholder"><ha-icon
    icon="mdi:cctv"></ha-icon><span data-i18n="noSnapshot">Snapshot non disponibile</span></div><img id="snapshot" alt="">
    <video id="live-video" autoplay playsinline muted hidden></video>
    <div id="legacy-live" hidden></div>
    <div id="live-loader" hidden aria-hidden="true"></div>
    <div id="talk-status" role="status" hidden></div>
    <div id="live-message" role="status" hidden></div>
    <button id="continue" class="primary" hidden data-copy="Continua?">Continua?</button>
    <button id="fullscreen" hidden aria-label="Schermo intero" title="Schermo intero"
      data-copy-aria-label="Schermo intero" data-copy-title="Schermo intero" aria-pressed="false">
      <ha-icon icon="mdi:fullscreen"></ha-icon></button>
    <button id="rotate" hidden aria-label="Ruota visualizzazione" title="Ruota visualizzazione" aria-pressed="false"
      data-copy-aria-label="Ruota visualizzazione" data-copy-title="Ruota visualizzazione"><ha-icon icon="mdi:screen-rotation"></ha-icon></button>
    <button id="record-live" hidden aria-label="Registrazione live" title="Registrazione live"
      data-copy-aria-label="Registrazione live" data-copy-title="Registrazione live" aria-expanded="false">
      <ha-icon icon="mdi:record-rec"></ha-icon></button>
    <div class="stage-actions"><button class="primary" id="live" title="Apri live">
      <ha-icon icon="mdi:video-wireless-outline"></ha-icon><span data-copy="Apri live">Apri live</span></button>
      <button id="refresh" title="Richiedi un nuovo snapshot alla telecamera" data-i18n-title="refreshSnapshot">
      <ha-icon icon="mdi:camera-retake-outline"></ha-icon><span data-i18n="refreshSnapshot">Aggiorna snapshot</span></button>
      <button id="motion"><ha-icon id="motion-icon" icon="mdi:motion-sensor"></ha-icon>
      <span id="motion-label"><span data-copy="Movimento">Movimento</span></span></button>
      <button id="speaker" hidden><ha-icon id="speaker-icon" icon="mdi:volume-off"></ha-icon>
      <span id="speaker-label" data-copy="Attiva audio">Attiva audio</span></button>
      <button id="microphone" hidden aria-describedby="live-message">
      <ha-icon id="microphone-icon" icon="mdi:microphone-off"></ha-icon>
      <span id="microphone-label" data-copy="Tieni premuto per parlare">Tieni premuto per parlare</span></button></div></div>
  <div class="media-body"><div class="media-title"><div><h3 id="camera-name"><span data-copy="Telecamera">Telecamera</span></h3>
    <div class="muted" id="camera-position"></div><div class="muted" id="snapshot-time"></div>
    </div><span class="badge off" id="camera-state"><span data-copy="Non disponibile">Non disponibile</span></span></div>
    <div class="facts"><div class="fact"><ha-icon id="battery-icon" icon="mdi:battery"></ha-icon>
      <div><span data-i18n="battery"><span data-copy="Batteria">Batteria</span></span><strong id="battery">—</strong></div></div>
      <div class="fact"><ha-icon icon="mdi:thermometer"></ha-icon><div><span data-i18n="temperature"><span data-copy="Temperatura">Temperatura</span></span>
      <strong id="temperature">—</strong></div></div>
      <div class="fact"><ha-icon icon="mdi:video-box"></ha-icon><div><span data-i18n="recentClips">Clip recenti</span>
      <strong id="clips">0</strong></div></div></div>
    <div class="actions"><button id="details">
      <ha-icon icon="mdi:cog-outline"></ha-icon><span data-i18n="detailsSettings">Dettagli e impostazioni</span></button>
      </div>
    <p class="muted" id="microphone-unavailable" hidden data-copy="Questo live non supporta ancora l’invio della voce alla telecamera da Vistoda.">Questo live non supporta ancora l’invio della voce alla telecamera da Vistoda.</p>
    <div class="muted" id="message" role="status"></div>
    <details id="recording-section"><summary data-copy="Registrazione live locale">Registrazione live locale</summary>
    <vistoda-provider-recordings id="recordings"></vistoda-provider-recordings></details></div>
</section>
<dialog id="mobile-live-dialog" aria-label="Live Blink"><div id="mobile-stage-slot"></div></dialog>
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
