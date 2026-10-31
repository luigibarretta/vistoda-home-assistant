// Markup of the EZVIZ events card: styles, rows and pager (no state, no network).
import { copy } from "./panel-copy.js";
import { PAGE_SIZE_TEMPLATE } from "./archive-page-size.js";
import { alarmIsoTime, alarmTimeText } from "./ezviz-alarm-model.js";

export const html = (value) => String(value ?? "").replace(/[&<>"']/g, (character) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
})[character]);

const STYLE = `
      :host{display:block;margin-top:14px}[hidden]{display:none!important}
      .head{display:flex;align-items:center;gap:8px}.head h3{flex:1;margin:0;font-size:16px}
      button{min-width:44px;min-height:44px;border:0;border-radius:12px;background:transparent;color:var(--primary-text-color);cursor:pointer}
      button:focus-visible,a:focus-visible{outline:2px solid var(--primary-color);outline-offset:2px}
      ul{list-style:none;margin:6px 0 0;padding:0}li{display:flex;align-items:center;gap:12px;min-height:56px;
        padding:6px 0;border-top:1px solid var(--divider-color,#ffffff1f)}
      .thumb,.icon{flex:none;width:72px;height:44px;border-radius:8px;overflow:hidden}
      .thumb img{width:100%;height:100%;object-fit:cover;display:block}
      .icon{display:grid;place-content:center;background:color-mix(in srgb,var(--primary-color) 12%,transparent);color:var(--primary-color)}
      .text{flex:1;min-width:0}.text strong{display:block}.title{color:var(--secondary-text-color);font-size:13px;overflow-wrap:anywhere}
      time{color:var(--secondary-text-color);font-size:13px;white-space:nowrap}.status{color:var(--secondary-text-color);margin:8px 0 0}
      .archive-pager{display:grid;grid-template-columns:auto 1fr auto;align-items:center;gap:10px;margin-top:12px}
      .archive-pager span{text-align:center;color:var(--secondary-text-color);font-size:13px}
      .archive-pager button{display:flex;align-items:center;gap:4px;padding:0 10px}
      .archive-pager button:disabled{opacity:.45;cursor:not-allowed}
      @media (max-width:600px){.archive-pager{grid-template-columns:1fr 1fr}.archive-pager span{grid-column:1 / -1;grid-row:1}}
      li[role=button]{cursor:pointer;border-radius:8px}li[role=button]:focus-visible{outline:2px solid var(--primary-color);outline-offset:2px}`;

// `view` is an alarmPage-shaped page; rows open the event modal by index.
export function alarmsTemplate(host, { view, status, busy, entryId, hasRows, locale }) {
  return `<style>${STYLE}
    </style><div class="head"><h3 data-copy="Eventi">Eventi</h3>
      <button id="reload" aria-label="Aggiorna eventi" title="Aggiorna eventi" data-copy-aria-label="Aggiorna eventi"
        data-copy-title="Aggiorna eventi" ${entryId ? "" : "disabled"}><ha-icon icon="mdi:refresh"></ha-icon></button></div>
      ${status ? `<p class="status" role="status">${html(status)}</p>` : ""}
      <div ${hasRows ? "" : "hidden"}>${PAGE_SIZE_TEMPLATE.replace("<vistoda-page-size ", '<vistoda-page-size unit="events" ')}</div>
      <ul aria-label="${html(copy(host, "Eventi"))}">${view.rows.map((row, index) => `<li role="button" tabindex="0" data-index="${index}">
        <span class="thumb" data-id="${html(row.id)}" hidden>
          <img alt="${html(copy(host, "Immagine evento: {p0}", { p0: copy(host, row.label) }))}" loading="lazy"></span>
        <span class="icon" aria-hidden="true"><ha-icon icon="${html(row.icon)}"></ha-icon></span>
        <span class="text"><strong>${html(copy(host, row.label))}</strong>
          ${row.title ? `<span class="title">${html(row.title)}</span>` : ""}</span>
        <time datetime="${html(alarmIsoTime(row.occurredAt))}">${html(alarmTimeText(row.occurredAt, locale))}</time></li>`).join("")}</ul>
      <nav class="archive-pager" aria-label="${html(copy(host, "Pagine eventi"))}" ${view.hasPrevious || view.hasNext ? "" : "hidden"}>
        <button id="previous" ${busy || !view.hasPrevious ? "disabled" : ""}><ha-icon icon="mdi:chevron-left"></ha-icon>
          <span>${html(copy(host, "Precedente"))}</span></button>
        <span id="page-label">${html(view.totalPages === null
          ? copy(host, "Pagina {p0}", { p0: view.page })
          : copy(host, "Pagina {p0} di {p1}", { p0: view.page, p1: view.totalPages }))}</span>
        <button id="next" ${busy || !view.hasNext ? "disabled" : ""}><span>${html(copy(host, "Successiva"))}</span>
          <ha-icon icon="mdi:chevron-right"></ha-icon></button></nav>`;
}
