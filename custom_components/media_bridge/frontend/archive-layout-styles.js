// Shared archive filters retain native keyboard/mobile picker behavior.
export const ARCHIVE_SELECT_STYLE = `
    min-height:44px; box-sizing:border-box;
    padding:9px 38px 9px 12px; border:1px solid var(--divider-color); border-radius:13px;
    color:var(--primary-text-color); background-color:var(--secondary-background-color);
    font:inherit; color-scheme:dark; appearance:none; -webkit-appearance:none;
    background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Cpath d='m4 6 4 4 4-4' fill='none' stroke='%23aaa' stroke-width='2'/%3E%3C/svg%3E");
    background-repeat:no-repeat; background-position:right 12px center; background-size:16px;
`;
export const ARCHIVE_FILTER_STYLES = `
  .archive-filter { display:grid; gap:8px; margin:16px 0; min-width:0; }
  .archive-filter label { color:var(--secondary-text-color); font-size:13px; font-weight:650; }
  .archive-filter select { ${ARCHIVE_SELECT_STYLE} display:block; width:100%; min-width:0; }
  .archive-filter select:focus-visible { outline:3px solid var(--primary-color); outline-offset:2px; }
`;

export const NETWORK_ARCHIVE_STYLES = `
  :host { display:block; min-width:0; min-height:0; } [hidden] { display:none !important; }
  header,.archive-toolbar,.row-actions,.archive-pagination { display:flex; align-items:center; gap:8px; }
  header,.archive-toolbar { justify-content:space-between; }
  header h3 { margin:0; } header { margin:16px 0; }
  .row { display:grid; grid-template-columns:minmax(0,1fr) auto; align-items:center;
    gap:12px; padding:16px 0; border-bottom:1px solid var(--divider-color); }
  .row>div:first-child { min-width:0; overflow-wrap:anywhere; }
  .row-actions { flex-wrap:nowrap; gap:4px; }
  .icon-action { flex:0 0 44px; width:44px; height:44px; padding:0; }
  .select-clip { display:grid; place-items:center; width:44px; height:44px; cursor:pointer; }
  .select-clip input { width:20px; height:20px; margin:0; accent-color:var(--primary-color); }
  .archive-toolbar { position:sticky; top:8px; background:var(--secondary-background-color);
    padding:8px 12px; border-radius:13px; z-index:1; margin:16px 0; }
  .archive-pagination { justify-content:space-between; margin-top:16px; }
  .archive-pagination span { text-align:center; font-size:13px; }
  code { display:block; overflow-wrap:anywhere; } video { width:100%; max-height:60vh; background:#000; }
  .muted { font-size:13px; } a { color:var(--primary-color); }
  @media (max-width:420px) {
    .row { grid-template-columns:minmax(0,1fr) 44px; gap:8px; }
    .row-actions { display:contents; }
    .select-clip { grid-column:2; grid-row:1; }
    .row-actions button { grid-row:2; }
    .row-actions button:first-of-type { justify-self:end; }
  }
`;
