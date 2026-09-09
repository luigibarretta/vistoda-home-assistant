export const BLINK_STORAGE_STYLES = `
  :host { display:block; margin-top:18px; }
  .storage { padding:18px; }
  header { display:flex; justify-content:space-between; align-items:flex-start; gap:14px; }
  .header-actions, .clip-actions { display:flex; flex-wrap:wrap; justify-content:flex-end; gap:8px; }
  h3 { margin:3px 0 4px; font-size:20px; }
  .module { margin-top:14px; border:1px solid var(--divider-color); border-radius:15px;
    overflow:hidden; }
  .module summary { display:flex; align-items:center; justify-content:space-between; gap:12px;
    min-height:58px; padding:12px 14px; cursor:pointer; }
  .module-body { padding:0 14px 14px; }
  .module-facts { display:flex; flex-wrap:wrap; gap:8px; margin-bottom:10px; }
  .module-facts span { padding:6px 9px; border-radius:999px; font-size:12px;
    background:var(--secondary-background-color); }
  .clip { display:flex; align-items:center; justify-content:space-between; gap:12px;
    min-height:62px; padding:10px 0; border-top:1px solid var(--divider-color); }
  .clip strong, .clip small { display:block; }
  .clip small { margin-top:3px; color:var(--secondary-text-color); }
  .player { margin:14px 0; padding:12px; border:1px solid var(--divider-color);
    border-radius:15px; background:var(--secondary-background-color); }
  .player[hidden] { display:none !important; }
  .player-head { display:flex; align-items:center; justify-content:space-between; gap:10px;
    margin-bottom:10px; }
  .player video { display:block; width:100%; max-height:62vh; border-radius:12px; background:#000; }
  .archive-pager { display:grid; grid-template-columns:auto 1fr auto; align-items:center;
    gap:10px; margin-top:12px; padding-top:12px; border-top:1px solid var(--divider-color); }
  .archive-pager span { text-align:center; color:var(--secondary-text-color); font-size:13px; }
  .readonly-note { margin-top:14px; padding:11px; border-radius:12px;
    background:color-mix(in srgb,var(--primary-color) 10%,transparent); }
  @media (max-width:650px) {
    .storage { padding:15px; } header, .clip { align-items:stretch; flex-direction:column; }
    .header-actions, .clip-actions { justify-content:stretch; }
    .header-actions button, .clip-actions button { flex:1 1 auto; }
    .archive-pager { grid-template-columns:1fr 1fr; }
    .archive-pager span { grid-column:1 / -1; grid-row:1; }
  }
`;
