export const blinkStorageTemplate = (styles, listTemplate, bulkListTemplate) => `<style>${styles}</style>
  <section class="card storage"><header><div><div class="eyebrow">Sync Module</div>
    <h3>Archivio Blink su chiavetta USB</h3><div class="muted">File presenti sul supporto
    collegato al bridge Blink.</div></div><div class="header-actions"><button id="backup-all"
    title="Backup archivio Blink" data-tooltip="Copia e verifica su NFS tutte le clip disponibili">
    <ha-icon icon="mdi:cloud-upload"></ha-icon>Backup archivio</button><button id="reload"
    title="Rileggi chiavetta" data-tooltip="Rilegge stato, spazio e indice della chiavetta Blink">
    <ha-icon icon="mdi:refresh"></ha-icon>Rileggi chiavetta</button></div></header>
    ${listTemplate}${bulkListTemplate}
    <section class="player" id="player" hidden><div class="player-head"><strong
    id="player-title">Riproduzione clip</strong><button class="icon-action" id="close-player"
    aria-label="Chiudi riproduzione" title="Chiudi riproduzione" data-tooltip="Chiudi il video">
    <ha-icon icon="mdi:close"></ha-icon></button></div>
    <video id="video" controls playsinline preload="metadata"></video></section>
    <div class="bulk-actions" id="bulk-actions" hidden><strong id="selected-count">0 selezionate</strong>
      <div class="bulk-buttons">
      <button class="icon-action" id="add-selected-to-lists" aria-label="Aggiungi selezionate alle liste"
      title="Aggiungi selezionate alle liste" data-tooltip="Aggiungi tutte le clip selezionate a una o più liste">
      <ha-icon icon="mdi:playlist-plus"></ha-icon></button>
      <button class="icon-action danger" id="delete-selected" aria-label="Elimina clip selezionate"
      title="Elimina clip selezionate" data-tooltip="Elimina definitivamente le clip selezionate">
      <ha-icon icon="mdi:delete-sweep-outline"></ha-icon></button></div></div>
    <div id="content"></div><div class="muted" id="status" role="status"></div>
    <div class="readonly-note muted"><strong>Gestione protetta.</strong> Riproduzione, download e
    backup non modificano la chiavetta. Eliminazione e formattazione richiedono privilegi
    amministrativi e una conferma esplicita.</div></section>
    <dialog id="format-dialog" aria-labelledby="format-title"><form method="dialog">
      <h4 id="format-title">Formattare la chiavetta Blink?</h4><p>Questa operazione elimina
      definitivamente tutte le clip dal supporto selezionato e non può essere annullata.</p>
      <p class="format-target" id="format-target"></p><label for="format-confirmation">Scrivi
      <strong id="format-phrase"></strong> per continuare</label><input id="format-confirmation"
      autocomplete="off" spellcheck="false"><div class="dialog-actions"><button value="cancel"
      id="cancel-format">Annulla</button><button value="confirm" class="danger" id="confirm-format"
      disabled>Formatta definitivamente</button></div></form></dialog>`;
