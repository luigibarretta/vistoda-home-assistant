export const BASE_STYLES = `
  :host { display:block; min-height:100%; color:var(--primary-text-color); }
  * { box-sizing:border-box; }
  .card { border:1px solid var(--divider-color); border-radius:22px;
    background:var(--card-background-color); box-shadow:var(--ha-card-box-shadow); }
  button, .button { min-height:44px; border:0; border-radius:13px; padding:9px 14px;
    cursor:pointer; font:inherit; font-weight:650; color:var(--primary-text-color);
    background:var(--secondary-background-color); text-decoration:none; }
  button.primary, .button.primary { color:#fff;
    background:linear-gradient(135deg,#6246ea,#4967e9); }
  button.danger { color:#fff; background:linear-gradient(135deg,#d84d75,#f47740); }
  button:disabled { opacity:.48; cursor:not-allowed; }
  .eyebrow { color:var(--primary-color); font-size:12px; font-weight:750;
    letter-spacing:.08em; text-transform:uppercase; }
  .muted { color:var(--secondary-text-color); line-height:1.45; }
  .badge { display:inline-flex; align-items:center; gap:6px; border-radius:999px;
    padding:7px 11px; font-size:13px; font-weight:700;
    background:color-mix(in srgb,var(--success-color,#43a047) 18%,transparent); }
  .badge.off { background:color-mix(in srgb,var(--error-color,#db4437) 16%,transparent); }
  .actions { display:flex; flex-wrap:wrap; gap:10px; }
  .empty { padding:30px; text-align:center; }
  @media (max-width:600px) { .actions > * { flex:1 1 100%; } }
`;

export const MEDIA_STYLES = `
  .provider-head { display:flex; justify-content:space-between; gap:18px;
    align-items:flex-start; margin-bottom:18px; }
  .provider-head h2 { margin:4px 0 5px; font-size:23px; }
  .media-card { overflow:hidden; }
  .stage { position:relative; aspect-ratio:16/9; min-height:220px;
    display:grid; place-items:center; background:#111; }
  .stage img { width:100%; height:100%; object-fit:cover; position:absolute; inset:0; }
  .stage .placeholder { color:#ddd; text-align:center; padding:20px; }
  .stage .placeholder ha-icon { --mdc-icon-size:48px; display:block; margin:0 auto 10px; }
  .media-body { padding:20px; }
  .media-title { display:flex; align-items:flex-start; justify-content:space-between; gap:15px; }
  .media-title h3 { margin:0 0 5px; font-size:21px; }
  .facts { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:10px;
    margin:16px 0; }
  .fact { padding:12px; border-radius:13px; background:var(--secondary-background-color); }
  .fact span { display:block; color:var(--secondary-text-color); font-size:12px; margin-bottom:4px; }
  .fact strong { font-size:14px; }
  .pager { display:flex; justify-content:center; align-items:center; gap:9px; margin-top:14px; }
  .pager button { min-width:44px; padding:8px; }
  .dots { display:flex; gap:6px; }
  .dot { width:10px; height:10px; min-height:10px; padding:0; border-radius:50%;
    background:var(--divider-color); }
  .dot.active { background:var(--primary-color); transform:scale(1.15); }
  .system { padding:18px; margin-bottom:16px; display:flex; align-items:center;
    justify-content:space-between; gap:18px; }
  @media (max-width:650px) {
    .facts { grid-template-columns:1fr; }
    .system, .provider-head { flex-direction:column; }
    .stage { min-height:180px; }
  }
`;
