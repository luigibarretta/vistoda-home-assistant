export const PROVIDER_RECORDING_STYLES = `
  [hidden] { display:none !important; }
  :host { display:block; margin-top:18px; padding-top:18px;
    border-top:1px solid var(--divider-color); }
  .head, .capture { display:flex; align-items:center; justify-content:space-between; gap:12px; }
  .head-actions { display:flex; flex-wrap:wrap; justify-content:flex-end; gap:8px; }
  h4 { margin:0; font-size:17px; }
  .capture { justify-content:flex-start; flex-wrap:wrap; margin:12px 0; }
  select { min-height:44px; padding:8px 34px 8px 12px; border:1px solid var(--divider-color);
    border-radius:12px; color:var(--primary-text-color); background:var(--card-background-color); }
  details { margin-top:12px; }
  summary { min-height:44px; display:flex; align-items:center; gap:8px; cursor:pointer;
    font-weight:700; list-style:none; }
  summary::-webkit-details-marker { display:none; }
  summary::before { content:"›"; font-size:22px; transition:transform .15s ease; }
  details[open] summary::before { transform:rotate(90deg); }
  .list { display:grid; gap:10px; margin-top:8px; }
  .item { position:relative; display:grid; grid-template-columns:auto minmax(0,1fr) auto; gap:10px;
    align-items:center; padding:12px; border-radius:14px;
    background:var(--secondary-background-color); }
  .item[aria-selected="true"] { box-shadow:inset 0 0 0 2px var(--primary-color); }
  .meta { display:flex; flex-wrap:wrap; gap:5px 12px; margin-top:4px;
    color:var(--secondary-text-color); font-size:12px; }
  .item-actions { display:flex; flex-wrap:wrap; gap:7px; justify-content:flex-end; }
  .select-item { display:grid; place-items:center; width:44px; min-height:44px; }
  .select-item input { width:20px; height:20px; }
  .icon-action { width:42px; height:42px; min-width:42px; padding:0; display:grid;
    place-items:center; border-radius:11px; }
  .icon-action ha-icon { --mdc-icon-size:22px; }
  .bulk-actions { display:flex; align-items:center; justify-content:space-between; gap:10px;
    margin:10px 0; padding:9px 11px; border-radius:12px; background:var(--secondary-background-color); }
  .bulk-actions[hidden] { display:none !important; }
  .bulk-buttons { display:flex; align-items:center; gap:7px; margin-left:auto; }
  .archive-path { display:flex; align-items:center; gap:8px; margin:8px 0 2px; min-width:0; }
  .archive-path code { overflow-wrap:anywhere; color:var(--primary-text-color); }
  .archive-path button { flex:0 0 auto; }
  .status { font-size:12px; font-weight:750; color:var(--primary-color); }
  .message { min-height:20px; margin-top:8px; }
  .destination-note { margin-top:-5px; font-size:12px; }
  .archive-pager { display:grid; grid-template-columns:auto 1fr auto; align-items:center;
    gap:10px; margin-top:12px; }
  .archive-pager span { text-align:center; color:var(--secondary-text-color); font-size:13px; }
  @media (max-width:600px) {
    .head { grid-template-columns:1fr; align-items:stretch; }
    .head { display:grid; } .capture > * { flex:1 1 100%; }
    .head-actions { justify-content:stretch; }
    .head-actions button { flex:1 1 auto; }
    .item { grid-template-columns:minmax(0,1fr); align-items:start; padding-right:12px; }
    .item-actions { grid-column:1; justify-content:flex-start; }
    .select-item { display:none; position:absolute; right:8px; top:8px; z-index:2;
      width:36px; min-height:36px; border-radius:50%; background:var(--card-background-color); }
    :host([selection-mode]) .select-item { display:grid; }
    :host([selection-mode]) .item { padding-right:52px; touch-action:pan-x; }
    .bulk-actions { position:sticky; bottom:max(8px,env(safe-area-inset-bottom)); z-index:12;
      box-shadow:0 6px 24px #0008; }
    .archive-pager { grid-template-columns:1fr 1fr; }
    .archive-pager span { grid-column:1 / -1; grid-row:1; }
  }
`;
