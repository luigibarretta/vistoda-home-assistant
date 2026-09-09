export const BLINK_SETTING_STYLES = `
  :host { display:block; margin-top:18px; }
  .settings { padding:20px; }
  header { display:flex; justify-content:space-between; align-items:flex-start; gap:14px; }
  h3 { margin:3px 0 4px; font-size:21px; }
  .accordion { margin-top:18px; border:1px solid var(--divider-color); border-radius:16px;
    overflow:hidden; }
  .setting-section { border-top:1px solid var(--divider-color); }
  .setting-section:first-child { border-top:0; }
  .setting-section[hidden] { display:none; }
  summary { display:grid; grid-template-columns:32px minmax(0,1fr) 24px; gap:12px;
    align-items:center; min-height:74px; padding:15px; cursor:pointer; list-style:none;
    background:var(--card-background-color); }
  summary::-webkit-details-marker { display:none; }
  summary > ha-icon:first-child { color:var(--primary-color); --mdc-icon-size:26px; }
  .section-copy strong, .section-copy small { display:block; }
  .section-copy small { margin-top:3px; color:var(--secondary-text-color); line-height:1.35; }
  .chevron { color:var(--secondary-text-color); transition:transform .18s ease; }
  details[open] .chevron { transform:rotate(180deg); }
  .section-body { padding:0 16px 14px 60px; background:var(--card-background-color); }
  #summary { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:8px;
    margin:0 0 10px; }
  .datum { padding:11px; border-radius:12px; background:var(--secondary-background-color); }
  .datum span { display:block; color:var(--secondary-text-color); font-size:12px; }
  .datum strong { display:block; margin-top:3px; overflow-wrap:anywhere; }
  .field { display:flex; align-items:center; justify-content:space-between; gap:18px;
    min-height:68px; padding:12px 0; border-top:1px solid var(--divider-color); }
  .field:first-child { border-top:0; } .field strong { display:block; }
  .field small { display:block; margin-top:3px; color:var(--secondary-text-color); }
  .control { flex:0 0 auto; min-width:112px; text-align:right; }
  .toggle { display:inline-flex; align-items:center; justify-content:flex-end; gap:9px;
    min-width:148px; padding:5px 2px; background:transparent; }
  .toggle-state { min-width:82px; text-align:right; }
  .switch-track { position:relative; width:46px; height:26px; flex:0 0 46px;
    border:1px solid var(--divider-color); border-radius:999px;
    background:var(--disabled-color,var(--divider-color)); transition:background .16s ease; }
  .switch-track::after { content:""; position:absolute; top:3px; left:3px; width:18px;
    height:18px; border-radius:50%; background:var(--card-background-color,#fff);
    box-shadow:0 1px 3px rgba(0,0,0,.35); transition:transform .16s ease; }
  .toggle[aria-checked="true"] .switch-track { background:var(--primary-color); }
  .toggle[aria-checked="true"] .switch-track::after { transform:translateX(20px); }
  .quality { display:block; }
  .quality > div:first-child { margin-bottom:10px; }
  .quality .control { width:100%; text-align:left; }
  .quality-options { display:grid; width:100%; margin:0; padding:0; border:0; gap:0; }
  .quality-option { display:grid; grid-template-columns:24px minmax(0,1fr); gap:11px;
    align-items:start; min-height:72px; padding:14px 2px; cursor:pointer;
    border-top:1px solid var(--divider-color); }
  .quality-option:first-child { border-top:0; }
  .quality-option input { width:20px; height:20px; min-height:20px; margin:2px 0 0;
    padding:0; accent-color:var(--primary-color); }
  .quality-option strong, .quality-option small { text-align:left; }
  .quality-option small { line-height:1.4; }
  select, input { min-height:42px; max-width:150px; border:1px solid var(--divider-color);
    border-radius:10px; padding:7px; color:var(--primary-text-color);
    background:var(--secondary-background-color); font:inherit; }
  input[type="range"] { min-height:30px; width:145px; padding:0; }
  .text-control { display:flex; align-items:center; gap:8px; }
  .text-control input { width:min(210px,42vw); max-width:none; }
  .text-control button { min-height:42px; }
  .value { display:block; margin-top:3px; font-size:13px; }
  .readonly { color:var(--secondary-text-color); }
  .draft-actions { position:sticky; bottom:10px; z-index:5; display:flex; align-items:center;
    justify-content:flex-end; gap:9px; margin-top:14px; padding:10px; border-radius:14px;
    background:color-mix(in srgb,var(--card-background-color) 92%,transparent);
    border:1px solid var(--divider-color); box-shadow:var(--ha-card-box-shadow); }
  .draft-actions[hidden] { display:none; }
  #status { min-height:21px; margin-top:12px; }
  .notice { margin-top:16px; padding:12px; border-radius:12px;
    background:color-mix(in srgb,var(--primary-color) 10%,transparent); }
  @media (max-width:650px) {
    #summary { grid-template-columns:repeat(2,minmax(0,1fr)); }
    .settings { padding:16px; } .field { align-items:flex-start; }
    summary { grid-template-columns:28px minmax(0,1fr) 22px; gap:9px; padding:13px 10px; }
    .section-body { padding:0 10px 12px; }
    .control { min-width:96px; } .toggle { min-width:144px; }
    input[type="range"] { width:115px; }
  }
`;
