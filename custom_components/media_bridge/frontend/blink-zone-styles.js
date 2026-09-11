export const BLINK_ZONE_STYLES = `
  :host { display:block; margin-top:18px; }
  :host([embedded]) { margin-top:14px; }
  :host([embedded]) .zones { box-shadow:none; border:1px solid var(--divider-color);
    background:var(--secondary-background-color); }
  .zones { padding:20px; }
  header { display:flex; justify-content:space-between; align-items:flex-start; gap:14px; }
  h3 { margin:3px 0 4px; font-size:21px; }
  .tabs { display:flex; gap:8px; margin:16px 0 12px; }
  .tabs button { flex:1; border:1px solid var(--divider-color); }
  .tabs button.active { color:#fff; background:var(--primary-color); border-color:var(--primary-color); }
  .editor-viewport { max-width:100%; max-height:65vh; overflow:auto; overscroll-behavior:contain; }
  .editor { position:relative; overflow:hidden; aspect-ratio:16/9; min-width:1174px; min-height:660px;
    border-radius:15px; background:#111; touch-action:none; user-select:none; }
  .editor img { position:absolute; inset:0; width:100%; height:100%; object-fit:cover; }
  .grid { position:absolute; inset:0; display:grid; grid-template-columns:repeat(20,1fr);
    grid-template-rows:repeat(15,1fr); }
  .cell { min-width:0; min-height:0; padding:0; border:0; border-radius:0;
    outline:1px solid rgba(255,255,255,.3); outline-offset:-1px; background:rgba(12,12,12,.45); }
  .cell.active { background:rgba(77,199,103,.18); }
  .cell.private { background:rgba(22,22,22,.72); }
  .cell:focus-visible { z-index:2; outline:2px solid #fff; }
  .privacy-overlay { position:absolute; border:2px solid #00c781; background:rgba(0,0,0,.48);
    pointer-events:none; }
  .privacy-overlay button { position:absolute; top:3px; right:3px; width:32px; height:32px;
    min-width:32px; min-height:32px; padding:0; border-radius:50%; pointer-events:auto; }
  .privacy-overlay.preview { border-style:dashed; }
  .legend { display:flex; align-items:center; gap:8px; margin-top:10px; font-size:13px; }
  .swatch { width:14px; height:14px; border-radius:4px; background:rgba(77,199,103,.45); }
  .swatch.private { background:rgba(20,20,20,.72); border:1px solid #00c781; }
  .zone-actions { display:flex; flex-wrap:wrap; gap:9px; margin-top:14px; }
  .zone-actions .save { margin-left:auto; }
  #status { min-height:21px; margin-top:10px; }
  @media (max-width:650px) {
    .zones { padding:16px; }
    .zone-actions > * { flex:1 1 calc(50% - 9px); }
    .zone-actions .save { margin-left:0; }
  }
`;
