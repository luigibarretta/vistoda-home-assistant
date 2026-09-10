export const BLINK_STORAGE_STYLES = `
  :host { display:block; margin-top:18px; }
  .storage { padding:18px; }
  header { display:flex; justify-content:space-between; align-items:flex-start; gap:14px; }
  .header-actions, .clip-actions { display:flex; flex-wrap:wrap; justify-content:flex-end; gap:7px; }
  .header-actions button { display:inline-flex; align-items:center; gap:7px; }
  h3 { margin:3px 0 4px; font-size:20px; }
  .module { margin-top:14px; border:1px solid var(--divider-color); border-radius:15px;
    overflow:hidden; }
  .module summary { display:flex; align-items:center; justify-content:space-between; gap:12px;
    min-height:58px; padding:12px 14px; cursor:pointer; }
  .module-body { padding:0 14px 14px; }
  .module-facts { display:flex; flex-wrap:wrap; gap:8px; margin-bottom:10px; }
  .module-facts span { padding:6px 9px; border-radius:999px; font-size:12px;
    background:var(--secondary-background-color); }
  .clip { display:grid; grid-template-columns:auto minmax(0,1fr) auto; align-items:center; gap:10px;
    min-height:62px; padding:10px 0; border-top:1px solid var(--divider-color); }
  .clip strong, .clip small { display:block; }
  .clip small { margin-top:3px; color:var(--secondary-text-color); }
  .player { margin:14px 0; padding:12px; border:1px solid var(--divider-color);
    border-radius:15px; background:var(--secondary-background-color); }
  .player[hidden] { display:none !important; }
  .player-head { display:flex; align-items:center; justify-content:space-between; gap:10px;
    margin-bottom:10px; }
  .player video { display:block; width:100%; max-height:62vh; border-radius:12px; background:#000; }
  .select-clip { display:grid; place-items:center; width:40px; min-height:40px; }
  .select-clip input { width:20px; height:20px; }
  .icon-action { width:42px; height:42px; min-width:42px; padding:0; display:grid;
    place-items:center; border-radius:11px; }
  .icon-action ha-icon { --mdc-icon-size:22px; }
  .bulk-actions { display:flex; align-items:center; justify-content:space-between; gap:10px;
    margin:12px 0; padding:9px 11px; border-radius:12px; background:var(--secondary-background-color); }
  .bulk-actions[hidden] { display:none !important; }
  .format-action { width:36px; height:36px; min-width:36px; border-radius:999px; }
  .archive-pager { display:grid; grid-template-columns:auto 1fr auto; align-items:center;
    gap:10px; margin-top:12px; padding-top:12px; border-top:1px solid var(--divider-color); }
  .archive-pager span { text-align:center; color:var(--secondary-text-color); font-size:13px; }
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
    .clip { grid-template-columns:auto minmax(0,1fr); align-items:start; }
    .clip-actions { grid-column:2; justify-content:flex-start; }
    .archive-pager { grid-template-columns:1fr 1fr; }
    .archive-pager span { grid-column:1 / -1; grid-row:1; }
    .dialog-actions button { flex:1 1 auto; }
  }
`;
