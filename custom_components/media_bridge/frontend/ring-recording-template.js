import { BASE_STYLES } from "./panel-styles.js";

export function recordingArchiveTemplate() {
  return `
    <style>${BASE_STYLES}
      :host{display:block;margin-top:18px;padding-top:17px;border-top:1px solid var(--divider-color)}
      *{box-sizing:border-box}.head{display:flex;justify-content:space-between;gap:14px;
        align-items:flex-start}.head>div:first-child{min-width:0;flex:1}h3{margin:0 0 4px;font-size:16px}
      .hint{color:var(--secondary-text-color);font-size:14px;line-height:1.45}.storage{margin-top:3px;
        overflow-wrap:anywhere}.toolbar,.archive-controls,.view-switch,.list-controls,.list-form{display:flex;
        gap:7px;flex-wrap:wrap}button,select,input{min-height:38px;border:0;border-radius:11px;padding:7px 11px;
        font:inherit;color:var(--primary-text-color);background:var(--secondary-background-color)}
      button{cursor:pointer;font-weight:700;display:inline-flex;align-items:center;justify-content:center;gap:6px}
      button ha-icon{--mdc-icon-size:19px}button.danger{color:var(--error-color,#db4437)}
      button:disabled{opacity:.48;cursor:not-allowed}button[aria-pressed="true"]{color:#fff;
        background:var(--primary-color)}[hidden]{display:none!important}.archive-controls{margin-top:13px;
        justify-content:space-between;align-items:center}.view-switch{padding:3px;border-radius:13px;
        background:var(--secondary-background-color)}.view-switch button{background:transparent}
      .view-switch button[aria-pressed="true"]{color:var(--text-primary-color,#fff);
        background:var(--primary-color);box-shadow:0 2px 7px color-mix(in srgb,var(--primary-color) 38%,transparent)}
      .list-controls{flex:1;justify-content:flex-end}.list-controls select{max-width:270px;flex:1}
      .list-form{width:100%;justify-content:flex-end}.list-form input{min-width:190px;
        border:1px solid var(--divider-color);background:var(--card-background-color)}
      .list-manager{width:100%;padding:11px;border:1px solid var(--divider-color);border-radius:14px;
        background:color-mix(in srgb,var(--secondary-background-color) 62%,transparent)}
      .list-items{display:grid;gap:8px}.list-item{display:flex;align-items:center;justify-content:space-between;
        gap:10px;padding:8px;border-radius:10px;background:var(--card-background-color)}
      .list-item>div:first-child{display:grid;gap:2px;min-width:0}.list-item strong{overflow-wrap:anywhere}
      .list-item-actions,.list-edit{display:flex;gap:7px;align-items:center}.list-edit{width:100%}
      .list-edit input{flex:1;min-width:120px;border:1px solid var(--divider-color);
        background:var(--card-background-color)}.count{font-size:12px;font-weight:800;opacity:.75}
      .table-wrap{overflow-x:auto;margin-top:12px}table{width:100%;border-collapse:collapse;min-width:690px}
      th,td{text-align:left;padding:10px 8px;border-bottom:1px solid var(--divider-color)}
      th{font-size:12px;color:var(--secondary-text-color);text-transform:uppercase;letter-spacing:.04em}
      td{font-size:14px}.row-actions,.player,.path-line{display:flex;align-items:center;gap:7px;flex-wrap:wrap}
      .row-action{min-height:34px;padding:5px 9px}.detail-row td{padding:12px 8px;
        background:var(--secondary-background-color)}.recording-details>*+*{margin-top:12px;padding-top:12px;
        border-top:1px solid var(--divider-color)}.player audio{min-width:220px;flex:1;height:40px}
      .path-line{align-items:flex-start;justify-content:space-between}.path-copy{flex:none}
      code{font-family:var(--code-font-family,monospace);overflow-wrap:anywhere;word-break:break-word}
      .cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:11px;margin-top:13px}
      .recording-card{padding:15px;border:1px solid var(--divider-color);border-radius:16px;
        background:var(--secondary-background-color)}.recording-heading{display:flex;flex-direction:column;gap:4px}
      .recording-card>.row-actions{margin-top:12px}.card-detail{margin-top:13px;padding-top:13px;
        border-top:1px solid var(--divider-color)}.list-tags{display:flex;gap:5px;flex-wrap:wrap;margin-top:9px}
      .list-tags span{padding:4px 8px;border-radius:999px;font-size:12px;background:color-mix(in srgb,
        var(--primary-color) 15%,transparent)}.list-picker{display:grid;gap:8px}.list-picker label{display:flex;
        align-items:center;gap:9px;min-height:44px}.list-picker input{min-height:auto;width:20px;height:20px;
        accent-color:var(--primary-color)}.empty{text-align:center;padding:20px}.pager{display:flex;
        align-items:center;justify-content:flex-end;gap:9px;margin-top:12px}
      @media(max-width:620px){.head{display:block}.toolbar{margin-top:10px}.toolbar button{flex:1}
        .archive-controls{align-items:stretch}.view-switch{width:100%}.view-switch button{flex:1}
        .list-controls{justify-content:stretch}.list-controls select{max-width:none;min-width:0;width:100%}
        .list-form{justify-content:stretch}.list-form input{width:100%;flex:1}.pager{justify-content:space-between}
        .list-item{align-items:stretch;flex-direction:column}.list-item-actions button{flex:1}
        .list-edit{flex-wrap:wrap}.list-edit input{width:100%;flex-basis:100%}.list-edit button{flex:1}
        .cards{grid-template-columns:1fr}.recording-card .row-action{flex:1}.table-wrap .row-action span{display:none}}
    </style>
    <div class="head"><div><h3><span data-copy="Registrazioni salvate">Registrazioni salvate</span></h3><div class="hint" id="status"
      role="status"></div><div class="hint storage" id="storage"></div></div><div class="toolbar">
      <button id="reload"><ha-icon icon="mdi:refresh"></ha-icon><span data-copy="Aggiorna">Aggiorna</span></button>
      <button class="danger" id="delete-all" disabled><ha-icon icon="mdi:delete-sweep-outline">
      </ha-icon><span data-copy="Elimina tutte">Elimina tutte</span></button></div></div>
    <div class="archive-controls"><div class="view-switch" role="group" aria-label="Vista archivio" data-copy-aria-label="Vista archivio">
      <button id="view-cards" aria-pressed="false"><ha-icon icon="mdi:view-grid-outline"></ha-icon><span data-copy="Schede">Schede</span></button>
      <button id="view-rows" aria-pressed="false"><ha-icon icon="mdi:view-list-outline"></ha-icon><span data-copy="Tabella">Tabella</span></button>
      </div><div class="list-controls"><select id="list-filter" aria-label="Filtra per lista" data-copy-aria-label="Filtra per lista"></select>
      <button id="new-list"><ha-icon icon="mdi:playlist-plus"></ha-icon><span data-copy="Nuova lista">Nuova lista</span></button>
      <button id="manage-lists" aria-expanded="false"><ha-icon icon="mdi:playlist-edit"></ha-icon>
      Gestisci <span class="count" id="manage-count">0</span></button></div><form class="list-form"
      id="list-form" hidden>
      <input id="list-name" maxlength="64" autocomplete="off" placeholder="Nome della lista" data-copy-placeholder="Nome della lista"
        aria-label="Nome della nuova lista" data-copy-aria-label="Nome della nuova lista"><button type="submit"><span data-copy="Crea">Crea</span></button>
      <button type="button" id="cancel-list"><span data-copy="Annulla">Annulla</span></button></form>
      <section class="list-manager" id="list-manager" aria-label="Gestione liste" data-copy-aria-label="Gestione liste" hidden>
      <div class="hint" id="list-empty"><span data-copy="Non hai ancora creato liste personalizzate.">Non hai ancora creato liste personalizzate.</span></div>
      <div class="list-items" id="list-items"></div></section></div>
    <div class="cards" id="cards" hidden></div>
    <div class="table-wrap" id="table-wrap"><table><thead><tr><th><span data-copy="Data">Data</span></th><th><span data-copy="Durata">Durata</span></th>
      <th><span data-copy="Dimensione">Dimensione</span></th><th><span data-copy="Azioni">Azioni</span></th></tr></thead><tbody id="rows"></tbody></table></div>
    <div class="empty hint" id="empty" hidden><span data-copy="Nessuna registrazione locale.">Nessuna registrazione locale.</span></div>
    <nav class="pager" id="pager" aria-label="Pagine archivio" data-copy-aria-label="Pagine archivio"><button id="previous"
      aria-label="Pagina precedente" data-copy-aria-label="Pagina precedente"><ha-icon icon="mdi:chevron-left"></ha-icon></button>
      <span id="page-label"><span data-copy="Pagina 1 di 1">Pagina 1 di 1</span></span><button id="next" aria-label="Pagina successiva" data-copy-aria-label="Pagina successiva">
      <ha-icon icon="mdi:chevron-right"></ha-icon></button></nav>`;
}
