export const blinkStorageTemplate = (styles, listTemplate, bulkListTemplate) => `<style>${styles}</style>
  <section class="card storage"><header><div><div class="eyebrow">Sync Module</div>
    <h3><span data-copy="Archivio Blink su chiavetta USB">Archivio Blink su chiavetta USB</span></h3><div class="muted"><span data-copy="File presenti sul supporto collegato al bridge Blink.">File presenti sul supporto
    collegato al bridge Blink.</span></div></div><div class="header-actions"><button id="backup-all"
    title="Backup archivio Blink" data-copy-title="Backup archivio Blink" data-tooltip="Copia e verifica su NFS tutte le clip disponibili" data-copy-data-tooltip="Copia e verifica su NFS tutte le clip disponibili">
    <ha-icon icon="mdi:cloud-upload"></ha-icon><span data-copy="Backup archivio">Backup archivio</span></button><button id="reload"
    title="Rileggi chiavetta" data-copy-title="Rileggi chiavetta" data-tooltip="Rilegge stato, spazio e indice della chiavetta Blink" data-copy-data-tooltip="Rilegge stato, spazio e indice della chiavetta Blink">
    <ha-icon icon="mdi:refresh"></ha-icon><span data-copy="Rileggi chiavetta">Rileggi chiavetta</span></button></div></header>
    ${listTemplate}${bulkListTemplate}
    <section class="player" id="player" hidden><div class="player-head"><strong
    id="player-title"><span data-copy="Riproduzione clip">Riproduzione clip</span></strong><button class="icon-action" id="close-player"
    aria-label="Chiudi riproduzione" data-copy-aria-label="Chiudi riproduzione" title="Chiudi riproduzione" data-copy-title="Chiudi riproduzione" data-tooltip="Chiudi il video" data-copy-data-tooltip="Chiudi il video">
    <ha-icon icon="mdi:close"></ha-icon></button></div>
    <video id="video" controls playsinline preload="metadata"></video></section>
    <div class="bulk-actions" id="bulk-actions" hidden><strong id="selected-count"><span data-copy="0 selezionate">0 selezionate</span></strong>
      <div class="bulk-buttons">
      <button class="icon-action" id="add-selected-to-lists" aria-label="Aggiungi selezionate alle liste" data-copy-aria-label="Aggiungi selezionate alle liste"
      title="Aggiungi selezionate alle liste" data-copy-title="Aggiungi selezionate alle liste" data-tooltip="Aggiungi tutte le clip selezionate a una o più liste" data-copy-data-tooltip="Aggiungi tutte le clip selezionate a una o più liste">
      <ha-icon icon="mdi:playlist-plus"></ha-icon></button>
      <button class="icon-action danger" id="delete-selected" aria-label="Elimina clip selezionate" data-copy-aria-label="Elimina clip selezionate"
      title="Elimina clip selezionate" data-copy-title="Elimina clip selezionate" data-tooltip="Elimina definitivamente le clip selezionate" data-copy-data-tooltip="Elimina definitivamente le clip selezionate">
      <ha-icon icon="mdi:delete-sweep-outline"></ha-icon></button></div></div>
    <div id="content"></div><div class="muted" id="status" role="status"></div>
    <div class="readonly-note muted"><strong><span data-copy="Gestione protetta.">Gestione protetta.</span></strong> <span data-copy="Riproduzione, download e backup non modificano la chiavetta. Eliminazione e formattazione richiedono privilegi amministrativi e una conferma esplicita.">Riproduzione, download e
    backup non modificano la chiavetta. Eliminazione e formattazione richiedono privilegi
    amministrativi e una conferma esplicita.</span></div></section>
    <dialog id="format-dialog" aria-labelledby="format-title"><form method="dialog">
      <h4 id="format-title"><span data-copy="Formattare la chiavetta Blink?">Formattare la chiavetta Blink?</span></h4><p><span data-copy="Questa operazione elimina definitivamente tutte le clip dal supporto selezionato e non può essere annullata.">Questa operazione elimina
      definitivamente tutte le clip dal supporto selezionato e non può essere annullata.</span></p>
      <p class="format-target" id="format-target"></p><label for="format-confirmation">Scrivi
      <strong id="format-phrase"></strong> <span data-copy="per continuare">per continuare</span></label><input id="format-confirmation"
      autocomplete="off" spellcheck="false"><div class="dialog-actions"><button value="cancel"
      id="cancel-format"><span data-copy="Annulla">Annulla</span></button><button value="confirm" class="danger" id="confirm-format"
      disabled><span data-copy="Formatta definitivamente">Formatta definitivamente</span></button></div></form></dialog>`;
