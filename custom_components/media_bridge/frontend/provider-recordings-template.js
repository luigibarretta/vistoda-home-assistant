export const providerRecordingsTemplate = (styles, listTemplate, bulkListTemplate) => `<style>${styles}</style>
  <section><div class="head"><div><h4><span data-copy="Registrazione live locale">Registrazione live locale</span></h4>
    <div class="muted"><span data-copy="Cattura il flusso che stai visualizzando, senza creare eventi cloud.">Cattura il flusso che stai visualizzando, senza creare eventi cloud.</span></div>
    </div><div class="head-actions"><button id="backup-all" title="Backup archivio" data-copy-title="Backup archivio"
    data-tooltip="Copia su NFS tutte le registrazioni pronte non ancora presenti" data-copy-data-tooltip="Copia su NFS tutte le registrazioni pronte non ancora presenti">
    <ha-icon icon="mdi:cloud-upload"></ha-icon> <span data-copy="Backup archivio">Backup archivio</span></button><button id="reload"
    title="Rileggi archivio" data-copy-title="Rileggi archivio" data-tooltip="Aggiorna stati e file locali" data-copy-data-tooltip="Aggiorna stati e file locali">
    <ha-icon icon="mdi:refresh"></ha-icon> <span data-copy="Aggiorna archivio">Aggiorna archivio</span></button></div></div>
    <div class="capture"><label for="duration"><span data-copy="Durata">Durata</span></label><select id="duration">
      <option value="15" data-copy="15 secondi">15 secondi</option><option value="30" selected data-copy="30 secondi">30 secondi</option>
      <option value="60" data-copy="60 secondi">60 secondi</option></select><label for="destination"><span data-copy="Destinazione">Destinazione</span></label>
      <select id="destination"><option value="ha" data-copy="Archivio locale HA">Archivio locale HA</option>
      <option id="provider-storage" value="provider" disabled data-copy="Supporto della camera">Supporto della camera</option></select>
      <button class="primary" id="start" title="Registra il live localmente" data-copy-title="Registra il live localmente">
      <ha-icon icon="mdi:record-rec"></ha-icon><span><span data-copy="Registra live">Registra live</span></span></button></div>
    <div class="destination-note muted" id="destination-note"></div>
    <div class="archive-path muted" id="archive-path" hidden><span id="archive-owner"><span data-copy="Percorso interno add-on:">Percorso interno add-on:</span></span>
      <code id="archive-directory"></code><button class="icon-action" id="copy-archive-path"
      aria-label="Copia percorso archivio locale" data-copy-aria-label="Copia percorso archivio locale" title="Copia percorso archivio locale" data-copy-title="Copia percorso archivio locale"
      data-tooltip="Copia il percorso interno dell’archivio" data-copy-data-tooltip="Copia il percorso interno dell’archivio"><ha-icon icon="mdi:content-copy"></ha-icon></button></div>
    <div class="message muted" id="message" role="status"></div>
    <vistoda-provider-recording-player id="player"></vistoda-provider-recording-player>
    <details open><summary id="summary"><span data-copy="Archivio locale">Archivio locale</span></summary>${listTemplate}${bulkListTemplate}
    <div class="bulk-actions" id="bulk-actions" hidden><strong id="selected-count"><span data-copy="0 selezionate">0 selezionate</span></strong>
      <div class="bulk-buttons">
      <button class="icon-action" id="add-selected-to-lists" aria-label="Aggiungi selezionate alle liste" data-copy-aria-label="Aggiungi selezionate alle liste"
      title="Aggiungi selezionate alle liste" data-copy-title="Aggiungi selezionate alle liste" data-tooltip="Aggiungi tutte le clip selezionate a una o più liste" data-copy-data-tooltip="Aggiungi tutte le clip selezionate a una o più liste">
      <ha-icon icon="mdi:playlist-plus"></ha-icon></button>
      <button class="icon-action danger" id="delete-selected" aria-label="Elimina selezionate" data-copy-aria-label="Elimina selezionate"
      title="Elimina registrazioni selezionate" data-copy-title="Elimina registrazioni selezionate" data-tooltip="Elimina le registrazioni selezionate" data-copy-data-tooltip="Elimina le registrazioni selezionate">
      <ha-icon icon="mdi:delete-sweep-outline"></ha-icon></button></div></div><div class="list" id="list"></div>
    <nav class="archive-pager" aria-label="Pagine archivio" data-copy-aria-label="Pagine archivio"><button id="previous">
    <ha-icon icon="mdi:chevron-left"></ha-icon><span><span data-copy="Precedente">Precedente</span></span></button>
    <span id="page-label"><span data-copy="Pagina 1 di 1">Pagina 1 di 1</span></span><button id="next">
    <span><span data-copy="Successiva">Successiva</span></span><ha-icon icon="mdi:chevron-right"></ha-icon></button></nav>
    </details></section>`;
