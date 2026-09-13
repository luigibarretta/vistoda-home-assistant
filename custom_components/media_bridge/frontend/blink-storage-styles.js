export const BLINK_STORAGE_STYLES = `
  :host { display:block; margin-top:18px; }
  .storage { padding:18px; }
  header { display:flex; justify-content:space-between; align-items:flex-start; gap:14px; }
  .header-actions, .clip-actions { display:flex; flex-wrap:wrap; justify-content:flex-end; gap:7px; }
  .header-actions button { display:inline-flex; align-items:center; gap:7px; }
  h3 { margin:3px 0 4px; font-size:20px; }
  .module { margin-top:14px; border:1px solid var(--divider-color); border-radius:15px;
    overflow:visible; }
  .module summary { display:flex; align-items:center; justify-content:space-between; gap:12px;
    min-height:58px; padding:12px 14px; cursor:pointer; }
  .module-body { padding:0 14px 14px; }
  .sync-module-info { display:flex; align-items:center; gap:12px; padding:12px 0;
    border-top:1px solid var(--divider-color); }
  .sync-module-info > ha-icon { --mdc-icon-size:34px; color:var(--success-color,#43a047); }
  .sync-module-info small { display:block; margin-top:3px; color:var(--secondary-text-color); }
  .module-facts { display:flex; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:10px; }
  .module-facts .storage-fact { display:inline-flex; align-items:center; gap:6px; min-height:32px;
    padding:6px 9px; border-radius:999px; font-size:12px; line-height:1.2;
    background:var(--secondary-background-color); }
  .storage-fact ha-icon { --mdc-icon-size:17px; flex:0 0 auto; color:var(--primary-color); }
  .storage-fact span { display:inline-flex; align-items:center; min-height:18px; padding:0; }
  .storage-fact:focus::after, .storage-gauge:focus::after { opacity:1; visibility:visible;
    transform:translateY(0); }
  .storage-gauge { position:relative; display:grid; place-items:center; width:54px; height:54px;
    flex:0 0 54px; border-radius:50%; background:conic-gradient(var(--primary-color) var(--used),
      var(--divider-color) 0); }
  .storage-gauge::before { content:""; position:absolute; inset:7px; border-radius:50%;
    background:var(--card-background-color); }
  .storage-gauge strong { position:relative; z-index:1; font-size:12px; }
  .module-actions { display:flex; flex-wrap:nowrap; align-items:center; gap:7px; margin:4px 0 10px; }
  .module-actions button { width:42px; min-width:42px; padding:0; }
  .module-actions [aria-disabled="true"] { opacity:.48; cursor:not-allowed; }
  .clip { position:relative; display:grid; grid-template-columns:auto minmax(0,1fr) auto; align-items:center; gap:10px;
    min-height:62px; padding:10px 0; border-top:1px solid var(--divider-color); }
  .clip[aria-selected="true"] { padding-left:12px; box-shadow:inset 3px 0 var(--primary-color); }
  .clip strong, .clip small { display:block; }
  .clip small { margin-top:3px; color:var(--secondary-text-color); }
  .player { margin:14px 0; padding:12px; border:1px solid var(--divider-color);
    border-radius:15px; background:var(--secondary-background-color); }
  .player[hidden] { display:none !important; }
  .player-head { display:flex; align-items:center; justify-content:space-between; gap:10px;
    margin-bottom:10px; }
  .player video { display:block; width:100%; max-height:62vh; border-radius:12px; background:#000; }
  .select-clip { display:grid; place-items:center; width:44px; min-height:44px; }
  .select-clip input { width:20px; height:20px; }
  .icon-action { width:42px; height:42px; min-width:42px; padding:0; display:grid;
    place-items:center; border-radius:11px; }
  .icon-action ha-icon { --mdc-icon-size:22px; }
  .bulk-actions { display:flex; align-items:center; justify-content:space-between; gap:10px;
    margin:12px 0; padding:9px 11px; border-radius:12px; background:var(--secondary-background-color); }
  .bulk-actions[hidden] { display:none !important; }
  .bulk-buttons { display:flex; align-items:center; gap:7px; margin-left:auto; }
  .format-action { width:36px; height:36px; min-width:36px; border-radius:999px; }
  .format-action::after { left:0; right:auto; max-width:min(260px,calc(100vw - 32px)); }
  .archive-pager { display:grid; grid-template-columns:auto 1fr auto; align-items:center;
    gap:10px; margin-top:12px; padding-top:12px; border-top:1px solid var(--divider-color); }
  .archive-pager span { text-align:center; color:var(--secondary-text-color); font-size:13px; }
  .camera-filter { position:relative; width:min(100%,320px); margin:10px 0; overflow:visible; }
  .camera-filter > summary { min-height:44px; box-sizing:border-box; display:flex; align-items:center;
    padding:8px 38px 8px 12px; border:1px solid var(--divider-color); border-radius:12px;
    background:var(--secondary-background-color); cursor:pointer; list-style:none; }
  .camera-filter > summary::-webkit-details-marker { display:none; }
  .camera-filter > summary::after { content:"⌄"; position:absolute; right:14px; font-size:18px; }
  .camera-filter[open] > summary::after { transform:rotate(180deg); }
  #camera-filter-options { position:absolute; z-index:30; left:0; right:0; top:48px; display:grid;
    max-height:260px; overflow:auto; padding:8px; border:1px solid var(--divider-color);
    border-radius:12px; background:var(--card-background-color); box-shadow:0 12px 30px #0008; }
  #camera-filter-options label { display:flex; align-items:center; gap:9px; min-height:44px; padding:0 6px; }
  #camera-filter-options input { width:20px; height:20px; }
  .readonly-note { margin-top:14px; padding:11px; border-radius:12px;
    background:color-mix(in srgb,var(--primary-color) 10%,transparent); }
  dialog { width:min(460px,calc(100vw - 28px)); box-sizing:border-box; padding:0;
    border:1px solid var(--divider-color); border-radius:18px; color:var(--primary-text-color);
    background:var(--card-background-color); box-shadow:0 18px 55px #0007; }
  dialog::backdrop { background:#0009; }
  dialog form { display:grid; gap:13px; padding:20px; } dialog h4, dialog p { margin:0; }
  dialog label { display:grid; gap:7px; } dialog input { min-height:44px; box-sizing:border-box;
    padding:9px 12px; border:1px solid var(--divider-color); border-radius:11px;
    color:var(--primary-text-color); background:var(--secondary-background-color); }
  .format-target { padding:10px; border-radius:11px; background:var(--secondary-background-color); }
  .dialog-actions { display:flex; justify-content:flex-end; gap:8px; margin-top:4px; }
  @media (max-width:650px) {
    .storage { padding:15px; } header { align-items:stretch; flex-direction:column; }
    .header-actions { justify-content:stretch; }
    .header-actions button { flex:1 1 auto; }
    .clip { grid-template-columns:minmax(0,1fr); align-items:start; }
    .clip-actions { grid-column:1; justify-content:flex-start; }
    .select-clip { display:none; position:absolute; right:0; top:7px; z-index:2;
      width:36px; min-height:36px; border-radius:50%; background:var(--card-background-color); }
    :host([selection-mode]) .select-clip { display:grid; }
    :host([selection-mode]) .clip { touch-action:pan-x; }
    :host([selection-mode]) .clip > div:nth-child(2) { padding:0 42px 0 8px; }
    .clip[aria-selected="true"] { padding-left:0; box-shadow:none; }
    .clip[aria-selected="true"]::before { content:""; position:absolute; left:-10px; top:8px;
      bottom:8px; width:3px; border-radius:3px; background:var(--primary-color); }
    .clip-actions { flex-wrap:nowrap; gap:3px; }
    .bulk-actions { position:sticky; bottom:max(8px,env(safe-area-inset-bottom)); z-index:12;
      box-shadow:0 6px 24px #0008; }
    .archive-pager { grid-template-columns:1fr 1fr; }
    .archive-pager span { grid-column:1 / -1; grid-row:1; }
    .dialog-actions button { flex:1 1 auto; }
  }
`;
