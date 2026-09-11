import { copy } from "./panel-copy.js";
import { saveRingEntry } from "./ring-entry-selection.js";

export const RING_DEVICE_SELECTOR_STYLES = `
  .device-picker { margin-top:16px; min-width:0; }
  .device-picker-label { display:block; color:var(--secondary-text-color); font-size:13px;
    font-weight:600; letter-spacing:.02em; margin-bottom:8px; }
  .device-options { display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr));
    gap:10px; min-width:0; }
  .device-card { min-width:0; min-height:74px; padding:12px 13px; text-align:left;
    border:1px solid var(--divider-color); border-radius:13px; background:var(--secondary-background-color);
    color:var(--primary-text-color); font:inherit; cursor:pointer; transition:border-color .15s, box-shadow .15s; }
  .device-card:hover { border-color:var(--primary-color); }
  .device-card:focus-visible { outline:2px solid var(--primary-color); outline-offset:2px; }
  .device-card[aria-selected="true"] { border-color:var(--primary-color);
    box-shadow:0 0 0 2px color-mix(in srgb,var(--primary-color) 25%,transparent); }
  .device-card:disabled { cursor:wait; opacity:.65; }
  .device-card-name { display:block; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-weight:700; }
  .device-card-location { display:block; margin-top:4px; overflow:hidden; text-overflow:ellipsis;
    white-space:nowrap; color:var(--secondary-text-color); font-size:13px; }
  .device-card-status { display:flex; align-items:center; gap:5px; margin-top:7px;
    font-size:12px; color:var(--secondary-text-color); }
  .device-card-status::before { content:""; width:7px; height:7px; flex:0 0 7px;
    border-radius:50%; background:var(--secondary-text-color); }
  .device-card[aria-selected="true"] .device-card-status::before,
  .device-card[data-available="true"] .device-card-status::before { background:var(--success-color,#43a047); }
  .device-select { position:absolute; width:1px; height:1px; overflow:hidden; clip:rect(0 0 0 0);
    clip-path:inset(50%); white-space:nowrap; }
  @media (max-width:600px) { .device-options{display:flex; overflow-x:auto; padding:2px 2px 8px;
    margin-right:-2px; overscroll-behavior-inline:contain; scrollbar-width:thin}
    .device-card{flex:0 0 min(232px,78vw)} }`;

export const RING_DEVICE_SELECTOR_TEMPLATE = `
  <div class="device-picker" id="device-picker" hidden>
    <span class="device-picker-label" id="device-picker-label" data-copy="Seleziona Ring Intercom">Seleziona Ring Intercom</span>
    <div class="device-options" id="device-options" role="listbox" aria-labelledby="device-picker-label"></div>
    <select class="device-select" id="device-select" aria-label="Seleziona Ring Intercom"
      data-copy-aria-label="Seleziona Ring Intercom"></select>
  </div>`;

export function mountRingDeviceSelector(host) {
  host.$("device-select").addEventListener("change", (event) => host._selectEntry(event.target.value));
  host.$("device-options").addEventListener("click", (event) => {
    const card = event.target.closest(".device-card");
    if (card) host._selectEntry(card.dataset.entryId);
  });
  host.$("device-options").addEventListener("keydown", (event) => navigate(host, event));
}

export function renderRingDeviceSelector(host) {
  const select = host.$("device-select");
  const options = host.$("device-options");
  select.replaceChildren(...host._entries.map((entry) => option(host, entry)));
  options.replaceChildren(...host._entries.map((entry) => card(host, entry)));
  host.$("device-picker").hidden = host._entries.length < 2;
  select.hidden = host._entries.length < 2;
  if (!host._entry) return;
  select.value = host._entry.entry_id;
  options.querySelectorAll(".device-card").forEach((item) => {
    const selected = item.dataset.entryId === host._entry.entry_id;
    item.setAttribute("aria-selected", String(selected));
    item.tabIndex = selected ? 0 : -1;
  });
  saveRingEntry(host._storage, host._entry.entry_id);
}

export function setRingDeviceSelectorDisabled(host, disabled) {
  host.$("device-options")?.querySelectorAll(".device-card")
    .forEach((card) => { card.disabled = disabled; });
}

function option(host, entry) {
  const item = document.createElement("option");
  item.value = entry.entry_id;
  item.textContent = deviceName(entry) + (entry.location_name ? ` · ${entry.location_name}` : "")
    + (entry.available ? "" : copy(host, "· non disponibile"));
  return item;
}

function card(host, entry) {
  const item = document.createElement("button");
  const name = deviceName(entry);
  const location = entry.location_name || copy(host, "Location Ring");
  const available = entry.available ? copy(host, "Disponibile") : copy(host, "Non disponibile");
  item.type = "button"; item.className = "device-card"; item.dataset.entryId = entry.entry_id;
  item.dataset.available = String(Boolean(entry.available)); item.setAttribute("role", "option");
  item.setAttribute("aria-label", `${name}, ${location}, ${available}`);
  item.innerHTML = '<span class="device-card-name"></span><span class="device-card-location"></span><span class="device-card-status"></span>';
  item.querySelector(".device-card-name").textContent = name;
  item.querySelector(".device-card-location").textContent = location;
  item.querySelector(".device-card-status").textContent = available;
  return item;
}

function deviceName(entry) {
  return entry.device_name || (entry.name || "Ring Intercom").replace(/^Vistoda · /, "");
}

function navigate(host, event) {
  if (!["ArrowRight", "ArrowDown", "ArrowLeft", "ArrowUp", "Home", "End"].includes(event.key)) return;
  const cards = [...host.$("device-options").querySelectorAll(".device-card")];
  const current = cards.indexOf(event.target.closest(".device-card"));
  if (current < 0) return;
  event.preventDefault();
  const direction = ["ArrowRight", "ArrowDown"].includes(event.key) ? 1 : -1;
  const next = event.key === "Home" ? 0 : event.key === "End" ? cards.length - 1
    : (current + direction + cards.length) % cards.length;
  cards[next].focus();
}
