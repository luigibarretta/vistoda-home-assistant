export const BASE_STYLES = `
  :host { display:block; width:100%; max-width:100%; min-width:0; box-sizing:border-box;
    min-height:100%; color:var(--primary-text-color); overflow-wrap:anywhere; }
  * { box-sizing:border-box; }
  button, .button, select { min-width:44px !important; min-height:44px !important; }
  select { max-width:100%; }
  button:focus-visible, a:focus-visible, select:focus-visible, input:focus-visible {
    outline:3px solid var(--primary-color,#6246ea); outline-offset:3px; }
  input:not([type=checkbox]):not([type=radio]) { min-height:44px !important; }
  [hidden] { display:none !important; }
  .card { border:1px solid var(--divider-color); border-radius:22px;
    background:var(--card-background-color); box-shadow:var(--ha-card-box-shadow); }
  button, .button { min-height:44px; border:0; border-radius:13px; padding:9px 14px;
    display:inline-flex; align-items:center; justify-content:center; gap:7px;
    cursor:pointer; font:inherit; font-weight:650; line-height:1.2; color:var(--primary-text-color);
    background:var(--secondary-background-color); text-decoration:none; }
  button ha-icon, .button ha-icon { --mdc-icon-size:20px; flex:0 0 auto; }
  button.primary, .button.primary { color:#fff;
    background:linear-gradient(135deg,#6246ea,#4967e9); }
  button.danger { color:#fff; background:linear-gradient(135deg,#d84d75,#f47740); }
  button:disabled { opacity:.48; cursor:not-allowed; }
  [data-tooltip] { position:relative; }
  [data-tooltip]::after { content:attr(data-tooltip); position:absolute; z-index:20;
    top:calc(100% + 8px); right:0; width:max-content; max-width:min(260px,75vw);
    padding:8px 10px; border-radius:9px; color:var(--primary-text-color);
    background:var(--card-background-color); border:1px solid var(--divider-color);
    box-shadow:var(--ha-card-box-shadow); font-size:12px; font-weight:500; line-height:1.35;
    text-align:left; white-space:normal; opacity:0; visibility:hidden; pointer-events:none;
    transform:translateY(-3px); transition:opacity .14s ease,transform .14s ease; }
  [data-tooltip]:hover::after, [data-tooltip]:focus-visible::after {
    opacity:1; visibility:visible; transform:translateY(0); }
  .eyebrow { color:var(--primary-color); font-size:12px; font-weight:750;
    letter-spacing:.08em; text-transform:uppercase; }
  .muted { color:var(--secondary-text-color); line-height:1.45; }
  .badge { display:inline-flex; align-items:center; gap:6px; border-radius:999px; max-width:100%;
    padding:7px 11px; font-size:13px; font-weight:700;
    background:color-mix(in srgb,var(--success-color,#43a047) 18%,transparent); }
  .badge.off { background:color-mix(in srgb,var(--error-color,#db4437) 16%,transparent); }
  .actions { display:flex; flex-wrap:wrap; gap:10px; }
  .empty { padding:30px; text-align:center; }
  @media (prefers-reduced-motion:reduce) { *, *::before, *::after {
    animation:none !important; transition:none !important; scroll-behavior:auto !important; } }
  @media (max-width:600px) { .actions > * { flex:1 1 100%; } .empty { padding:20px; } }
`;

export const MEDIA_STYLES = `
  .provider-head { display:flex; justify-content:space-between; gap:18px;
    align-items:flex-start; margin-bottom:18px; }
  .provider-head h2 { margin:4px 0 5px; font-size:23px; }
  .media-card { overflow:hidden; }
  .stage { position:relative; aspect-ratio:16/9; min-height:220px;
    display:grid; place-items:center; background:#111; touch-action:pan-y; user-select:none; }
  .stage img { width:100%; height:100%; object-fit:cover; position:absolute; inset:0; }
  .stage .placeholder { color:#ddd; text-align:center; padding:20px; }
  .stage .placeholder ha-icon { --mdc-icon-size:48px; display:block; margin:0 auto 10px; }
  .media-body { padding:20px; }
  .media-title { display:flex; align-items:flex-start; justify-content:space-between; gap:15px; }
  .media-title > div { min-width:0; }
  .media-title h3 { margin:0 0 5px; font-size:21px; }
  #snapshot-time { margin-top:3px; font-size:13px; }
  .facts { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:10px;
    margin:16px 0; }
  .fact { display:grid; grid-template-columns:auto minmax(0,1fr); align-items:center; gap:10px;
    padding:12px; border-radius:13px; background:var(--secondary-background-color); }
  .fact > ha-icon { --mdc-icon-size:23px; color:var(--primary-color); }
  .fact span { display:block; color:var(--secondary-text-color); font-size:12px; margin-bottom:4px; }
  .fact strong { font-size:14px; }
  .pager { display:flex; justify-content:center; align-items:center; gap:9px; margin-top:14px; }
  .pager button { min-width:44px; padding:8px; }
  .dots { display:flex; align-items:center; justify-content:center; flex-wrap:wrap; gap:1px; min-width:0; }
  .pager button.dot { display:grid; place-items:center; width:44px; height:44px;
    min-width:44px; min-height:44px; flex:0 0 44px; padding:0; border-radius:50%;
    background:transparent; }
  .dot::before { content:""; width:8px; height:8px; border-radius:50%;
    background:var(--divider-color); transition:transform .16s ease,background .16s ease; }
  .dot.active::before { background:var(--primary-color); transform:scale(1.25); }
  .system { padding:18px; margin-bottom:16px; display:flex; align-items:center;
    justify-content:space-between; gap:18px; }
  @media (max-width:650px) {
    .facts { grid-template-columns:1fr; }
    .system, .provider-head { flex-direction:column; }
    .media-title { flex-wrap:wrap; }
    .stage { min-height:180px; }
  }
`;
