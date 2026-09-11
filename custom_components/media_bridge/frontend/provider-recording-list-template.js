export const PROVIDER_LIST_TEMPLATE = `
  <div class="list-controls"><select id="list-filter" aria-label="Filtra per lista" data-copy-aria-label="Filtra per lista">
    <option value="" data-copy="Tutte le registrazioni">Tutte le registrazioni</option></select>
    <button id="new-list"><ha-icon icon="mdi:playlist-plus"></ha-icon><span><span data-copy="Nuova lista">Nuova lista</span></span></button>
    <button id="manage-lists" aria-expanded="false"><ha-icon icon="mdi:playlist-edit"></ha-icon>
      <span><span data-copy="Gestisci liste">Gestisci liste</span></span><span class="count" id="manage-count">0</span></button></div>
  <form class="list-form" id="list-form" hidden><input id="list-name" maxlength="64"
    autocomplete="off" placeholder="Nome della lista" data-copy-placeholder="Nome della lista" aria-label="Nome della nuova lista" data-copy-aria-label="Nome della nuova lista">
    <button type="submit"><span data-copy="Crea">Crea</span></button><button type="button" id="cancel-list"><span data-copy="Annulla">Annulla</span></button></form>
  <section class="list-manager" id="list-manager" hidden><div class="muted" id="list-empty">
    <span data-copy="Non hai ancora creato liste.">Non hai ancora creato liste.</span></div><div id="list-items"></div></section>`;

export const PROVIDER_LIST_STYLES = `
  .list-controls { display:flex; flex-wrap:wrap; align-items:center; gap:8px; margin:12px 0; }
  .list-controls select { flex:1 1 190px; min-height:44px; box-sizing:border-box;
    padding:9px 38px 9px 12px; border:1px solid var(--divider-color); border-radius:13px;
    color:var(--primary-text-color); background-color:var(--secondary-background-color);
    font:inherit; color-scheme:dark; }
  .list-controls button { display:inline-flex; align-items:center; gap:7px; }
  .list-controls .count { display:grid; place-items:center; min-width:20px; min-height:20px;
    padding:0 5px; border-radius:999px; background:var(--secondary-background-color); font-size:11px; }
  .list-form, .list-edit { display:flex; flex-wrap:wrap; gap:8px; margin:10px 0; }
  .list-form input, .list-edit input { flex:1 1 180px; min-height:44px; box-sizing:border-box;
    padding:9px 12px; border:1px solid var(--divider-color); border-radius:11px;
    color:var(--primary-text-color); background:var(--card-background-color); }
  .list-manager { margin:10px 0 14px; padding:10px 12px; border:1px solid var(--divider-color);
    border-radius:14px; }
  .list-item { display:flex; align-items:center; justify-content:space-between; gap:10px;
    min-height:52px; border-top:1px solid var(--divider-color); }
  .list-item:first-child { border-top:0; }
  .list-item > div:first-child { display:grid; gap:2px; min-width:0; }
  .list-item-actions { display:flex; gap:6px; }
  .list-icon { width:42px; height:42px; min-width:42px; padding:0; display:grid; place-items:center; }
  .list-icon ha-icon { --mdc-icon-size:21px; }
  .list-picker { grid-column:1 / -1; display:grid; gap:8px; width:100%; margin-top:8px;
    padding:11px; box-sizing:border-box; border-radius:12px; background:var(--card-background-color); }
  .list-picker label { display:flex; align-items:center; gap:9px; min-height:44px; }
  .list-picker input { width:20px; height:20px; }
  .list-tags { display:flex; flex-wrap:wrap; gap:5px; margin-top:6px; }
  .list-tag { padding:3px 7px; border-radius:999px; font-size:11px;
    background:color-mix(in srgb,var(--primary-color) 13%,transparent); }
  @media (max-width:600px) {
    .list-controls > button { flex:1 1 auto; }
    .list-item { align-items:flex-start; padding:8px 0; }
  }`;
