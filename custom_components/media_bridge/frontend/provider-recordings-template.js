export const providerRecordingsTemplate = (styles, listTemplate, bulkListTemplate) => `<style>${styles}</style>
  <section><div class="head"><div><h4>Registrazione live locale</h4>
    <div class="muted">Cattura il flusso che stai visualizzando, senza creare eventi cloud.</div>
    </div><div class="head-actions"><button id="backup-all" title="Backup archivio"
    data-tooltip="Copia su NFS tutte le registrazioni pronte non ancora presenti">
    <ha-icon icon="mdi:cloud-upload"></ha-icon> Backup archivio</button><button id="reload"
    title="Rileggi archivio" data-tooltip="Aggiorna stati e file locali">
    <ha-icon icon="mdi:refresh"></ha-icon> Aggiorna archivio</button></div></div>
    <div class="capture"><label for="duration">Durata</label><select id="duration">
      <option value="15">15 secondi</option><option value="30" selected>30 secondi</option>
      <option value="60">60 secondi</option></select><label for="destination">Destinazione</label>
      <select id="destination"><option value="ha">Archivio locale HA</option>
      <option id="provider-storage" value="provider" disabled>Supporto della camera</option></select>
      <button class="primary" id="start" title="Registra il live localmente">
      <ha-icon icon="mdi:record-rec"></ha-icon><span>Registra live</span></button></div>
    <div class="destination-note muted" id="destination-note"></div>
    <div class="archive-path muted" id="archive-path" hidden><span id="archive-owner">Percorso interno add-on:</span>
      <code id="archive-directory"></code><button class="icon-action" id="copy-archive-path"
      aria-label="Copia percorso archivio locale" title="Copia percorso archivio locale"
      data-tooltip="Copia il percorso interno dell’archivio"><ha-icon icon="mdi:content-copy"></ha-icon></button></div>
    <div class="message muted" id="message" role="status"></div>
    <vistoda-provider-recording-player id="player"></vistoda-provider-recording-player>
    <details open><summary id="summary">Archivio locale</summary>${listTemplate}${bulkListTemplate}
    <div class="bulk-actions" id="bulk-actions" hidden><strong id="selected-count">0 selezionate</strong>
      <div class="bulk-buttons">
      <button class="icon-action" id="add-selected-to-lists" aria-label="Aggiungi selezionate alle liste"
      title="Aggiungi selezionate alle liste" data-tooltip="Aggiungi tutte le clip selezionate a una o più liste">
      <ha-icon icon="mdi:playlist-plus"></ha-icon></button>
      <button class="icon-action danger" id="delete-selected" aria-label="Elimina selezionate"
      title="Elimina registrazioni selezionate" data-tooltip="Elimina le registrazioni selezionate">
      <ha-icon icon="mdi:delete-sweep-outline"></ha-icon></button></div></div><div class="list" id="list"></div>
    <nav class="archive-pager" aria-label="Pagine archivio"><button id="previous">
    <ha-icon icon="mdi:chevron-left"></ha-icon><span>Precedente</span></button>
    <span id="page-label">Pagina 1 di 1</span><button id="next">
    <span>Successiva</span><ha-icon icon="mdi:chevron-right"></ha-icon></button></nav>
    </details></section>`;
