export const PROVIDER_RECORDING_STYLES = `
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
  .item { display:grid; grid-template-columns:minmax(0,1fr) auto; gap:10px;
    align-items:center; padding:12px; border-radius:14px;
    background:var(--secondary-background-color); }
  .meta { display:flex; flex-wrap:wrap; gap:5px 12px; margin-top:4px;
    color:var(--secondary-text-color); font-size:12px; }
  .item-actions { display:flex; flex-wrap:wrap; gap:7px; justify-content:flex-end; }
  .item-actions button { min-height:40px; padding:7px 10px; }
  .status { font-size:12px; font-weight:750; color:var(--primary-color); }
  .message { min-height:20px; margin-top:8px; }
  @media (max-width:600px) {
    .head, .item { grid-template-columns:1fr; align-items:stretch; }
    .head { display:grid; } .capture > * { flex:1 1 100%; }
    .head-actions { justify-content:stretch; }
    .head-actions button { flex:1 1 auto; }
    .item-actions { justify-content:stretch; }
    .item-actions button { flex:1 1 auto; }
  }
`;
