export function recordingArchiveTemplate() {
  return `
    <style>
      :host{display:block;margin-top:18px;padding-top:17px;border-top:1px solid var(--divider-color)}
      *{box-sizing:border-box}.head{display:flex;justify-content:space-between;gap:14px;
        align-items:flex-start}h3{margin:0 0 4px;font-size:16px}.hint{color:var(--secondary-text-color);
        font-size:14px;line-height:1.45}.storage{margin-top:3px;overflow-wrap:anywhere}.toolbar{display:flex;
        gap:7px;flex-wrap:wrap}button{min-height:38px;border:0;border-radius:11px;padding:7px 11px;
        cursor:pointer;font:inherit;font-weight:700;display:inline-flex;align-items:center;
        justify-content:center;gap:6px;color:var(--primary-text-color);
        background:var(--secondary-background-color)}button ha-icon{--mdc-icon-size:19px}
      button.danger{color:var(--error-color,#db4437)}button:disabled{opacity:.48;cursor:not-allowed}
      .table-wrap{overflow-x:auto;margin-top:12px}table{width:100%;border-collapse:collapse;min-width:620px}
      th,td{text-align:left;padding:10px 8px;border-bottom:1px solid var(--divider-color)}
      th{font-size:12px;color:var(--secondary-text-color);text-transform:uppercase;letter-spacing:.04em}
      td{font-size:14px}.row-actions,.player,.path-line{display:flex;align-items:center;gap:7px}
      .row-action{min-height:34px;padding:5px 9px}.player-row td,.info-row td{padding:12px 8px;
        background:var(--secondary-background-color)}.player{flex-wrap:wrap}.player audio{min-width:220px;
        flex:1;height:40px}.path-line{align-items:flex-start;justify-content:space-between}.path-copy{flex:none}
      code{font-family:var(--code-font-family,monospace);overflow-wrap:anywhere;word-break:break-word}
      .empty{text-align:center;padding:20px}.pager{display:flex;align-items:center;justify-content:flex-end;
        gap:9px;margin-top:12px}
      @media(max-width:520px){.head{display:block}.toolbar{margin-top:10px}.toolbar button{flex:1}
        .pager{justify-content:space-between}.row-action span{display:none}}
    </style>
    <div class="head"><div><h3>Registrazioni salvate</h3><div class="hint" id="status"
      role="status"></div><div class="hint storage" id="storage"></div></div><div class="toolbar">
      <button id="reload"><ha-icon icon="mdi:refresh"></ha-icon>Aggiorna</button>
      <button class="danger" id="delete-all" disabled><ha-icon icon="mdi:delete-sweep-outline">
      </ha-icon>Elimina tutte</button></div></div>
    <div class="table-wrap" id="table-wrap"><table><thead><tr><th>Data</th><th>Durata</th>
      <th>Dimensione</th><th>Azioni</th></tr></thead><tbody id="rows"></tbody></table></div>
    <div class="empty hint" id="empty" hidden>Nessuna registrazione locale.</div>
    <nav class="pager" aria-label="Pagine archivio"><button id="previous"
      aria-label="Pagina precedente"><ha-icon icon="mdi:chevron-left"></ha-icon></button>
      <span id="page-label">Pagina 1 di 1</span><button id="next" aria-label="Pagina successiva">
      <ha-icon icon="mdi:chevron-right"></ha-icon></button></nav>`;
}
