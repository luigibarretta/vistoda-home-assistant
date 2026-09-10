import { BASE_STYLES } from "./panel-styles.js";
import { BLINK_STORAGE_STYLES } from "./blink-storage-styles.js";
import { ProviderRecordingListManager, PROVIDER_LIST_STYLES,
  PROVIDER_LIST_TEMPLATE } from "./provider-recording-list-manager.js";
import { blinkStorageActions } from "./blink-storage-actions.js";
import { blinkStorageTemplate } from "./blink-storage-template.js";

class VistodaBlinkStorage extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._storages = []; this._busy = false; this._loaded = false;
    this._page = 1; this._pageSize = 10; this._selected = new Set();
    this._listManager = new ProviderRecordingListManager(this);
    this._mount();
  }

  set hass(value) { this.configure(value, this._config); }

  configure(hass, config) {
    this._hass = hass; this._config = config;
    this._listManager.configure(config);
    if (hass && !this._loaded && !this._busy) this.reload();
  }

  _mount() {
    this.shadowRoot.innerHTML = blinkStorageTemplate(
      BASE_STYLES + BLINK_STORAGE_STYLES + PROVIDER_LIST_STYLES, PROVIDER_LIST_TEMPLATE);
    this.$ = (id) => this.shadowRoot.getElementById(id);
    this.$("reload").addEventListener("click", () => this.reload());
    this.$("backup-all").addEventListener("click", () => this._backupAll());
    this.$("close-player").addEventListener("click", () => this._closePlayer());
    this.$("delete-selected").addEventListener("click", () => this._deleteSelected());
    this.$("format-confirmation").addEventListener("input", () => {
      this.$("confirm-format").disabled = this.$("format-confirmation").value !== this._formatPhrase;
    });
    this.$("format-dialog").addEventListener("close", () => {
      if (this.$("format-dialog").returnValue === "confirm") this._format();
    });
    this._listManager.mount(this.shadowRoot);
    this._render();
  }

  async _fetch(page, pageSize = this._pageSize) {
    return this._hass.callWS({ type: "blink_live_bridge/local_storage/list",
      page, page_size: pageSize });
  }

  async reload() {
    if (!this._hass || this._busy) return;
    this._busy = true; this._setMessage("Lettura indice USB Blink…"); this._render();
    try {
      const result = await this._fetch(this._page);
      this._storages = Array.isArray(result.storages) ? result.storages : [];
      this._loaded = true; this._setMessage("");
    } catch (_error) {
      this._setMessage("Archivio USB non disponibile o Sync Module senza supporto.");
    } finally { this._busy = false; this._render(); }
  }

  _render() {
    this.$("reload").disabled = this._busy || !this._hass;
    this.$("backup-all").disabled = this._busy || !this._hass;
    const nodes = this._storages.map((storage) => this._module(storage));
    if (!nodes.length && this._loaded) {
      const empty = document.createElement("div"); empty.className = "muted";
      empty.textContent = "Nessuna chiavetta USB Blink disponibile."; nodes.push(empty);
    }
    this.$("content").replaceChildren(...nodes);
    this.$("bulk-actions").hidden = this._selected.size === 0;
    this.$("selected-count").textContent = `${this._selected.size} selezionate`;
    this.$("delete-selected").disabled = this._busy;
  }

  _module(storage) {
    const details = document.createElement("details"); details.className = "module"; details.open = true;
    const summary = document.createElement("summary");
    const title = document.createElement("strong"); title.textContent = storage.network_name || "Sistema Blink";
    const count = document.createElement("span");
    count.textContent = `${storage.pagination?.total_items ?? storage.clips?.length ?? 0} clip`;
    summary.append(title, count);
    const body = document.createElement("div"); body.className = "module-body";
    const facts = document.createElement("div"); facts.className = "module-facts";
    facts.append(this._fact("mdi:usb-flash-drive",
      `USB: ${storage.status?.usb_state || "stato sconosciuto"}`));
    if (Number.isFinite(storage.status?.usb_storage_available_percentage)) {
      facts.append(this._fact("mdi:harddisk",
        `Spazio disponibile: ${storage.status.usb_storage_available_percentage}%`));
    }
    if (storage.status?.last_backup_completed) {
      facts.append(this._fact("mdi:cloud-check-outline",
        `Ultimo backup Blink: ${this._date(storage.status.last_backup_completed)}`));
    }
    if (storage.status?.can_format_usb) {
      const format = this._icon("mdi:format-page-break", "Formatta chiavetta",
        () => this._openFormat(storage), false, true);
      format.classList.add("format-action"); facts.append(format);
    }
    const clips = this._listManager.filtered(storage.clips || [], (clip) => this._mediaId(storage, clip));
    const rows = clips.map((clip) => this._clip(storage, clip));
    if (!rows.length) {
      const empty = document.createElement("div"); empty.className = "muted";
      empty.textContent = this._listManager.filterId
        ? "Nessuna clip di questa pagina appartiene alla lista." : "Nessuna clip indicizzata in questa pagina.";
      rows.push(empty);
    }
    body.append(facts, ...rows, this._pager(storage.pagination));
    details.append(summary, body); return details;
  }

  _clip(storage, clip) {
    const row = document.createElement("article"); row.className = "clip";
    const key = this._selectionKey(storage, clip); const mediaId = this._mediaId(storage, clip);
    const selector = document.createElement("label"); selector.className = "select-clip";
    const checkbox = document.createElement("input"); checkbox.type = "checkbox";
    checkbox.checked = this._selected.has(key); checkbox.disabled = this._busy || !storage.status?.can_delete_clips;
    checkbox.setAttribute("aria-label", `Seleziona clip ${clip.device_name || clip.id}`);
    checkbox.addEventListener("change", () => {
      checkbox.checked ? this._selected.add(key) : this._selected.delete(key); this._render();
    }); selector.append(checkbox);
    const text = document.createElement("div"); const title = document.createElement("strong");
    title.textContent = clip.device_name || "Telecamera Blink";
    const meta = document.createElement("small"); const duration = Number.isFinite(clip.clip_length_ms)
      ? ` · ${(clip.clip_length_ms / 1000).toFixed(1)} s` : "";
    meta.textContent = `${this._date(clip.created_at)}${duration}`; text.append(title, meta);
    const tags = this._listManager.tags(mediaId); if (tags) text.append(tags);
    const actions = document.createElement("div"); actions.className = "clip-actions";
    actions.append(this._icon("mdi:play", "Riproduci", () => this._play(storage, clip), !clip.media_available));
    actions.append(this._icon("mdi:download", "Scarica", () => this._download(storage, clip), !clip.media_available));
    actions.append(this._icon("mdi:cloud-upload", "Backup NFS", () => this._backupSingle(storage, clip), !clip.media_available));
    actions.append(this._icon("mdi:playlist-plus", "Aggiungi alle liste",
      () => this._listManager.toggle(mediaId), false));
    actions.append(this._icon("mdi:delete-outline", "Elimina clip",
      () => this._deleteOne(storage, clip), !storage.status?.can_delete_clips, true));
    row.append(selector, text, actions);
    if (this._listManager.openRecordingId === mediaId) row.append(this._listManager.picker(mediaId));
    return row;
  }

  _pager(pagination = {}) {
    const pager = document.createElement("nav"); pager.className = "archive-pager";
    pager.setAttribute("aria-label", "Pagine archivio Blink");
    const previous = this._button("mdi:chevron-left", "Precedente",
      () => this._go(pagination.page - 1), !pagination.has_previous);
    const label = document.createElement("span");
    label.textContent = `Pagina ${pagination.page || 1} di ${pagination.total_pages || 1}`;
    const next = this._button("mdi:chevron-right", "Successiva",
      () => this._go(pagination.page + 1), !pagination.has_next);
    pager.append(previous, label, next); return pager;
  }

  async _go(page) {
    if (page < 1 || this._busy) return;
    this._page = page; this._selected.clear(); this._closePlayer(); await this.reload();
  }

  _selectionKey(storage, clip) { return `${storage.network_id}:${storage.sync_module_id}:${storage.manifest_id}:${clip.id}`; }
  _mediaId(storage, clip) { return `usb:${this._selectionKey(storage, clip)}`; }
  _listsChanged(resetPage) { if (resetPage) this._page = 1; this._render(); }
  _setMessage(value) { if (this.$) this.$("status").textContent = value; }
  _button(icon, label, action, disabled = false) {
    const button = document.createElement("button");
    button.innerHTML = `<ha-icon icon="${icon}"></ha-icon><span>${label}</span>`;
    button.disabled = disabled || this._busy; button.addEventListener("click", action); return button;
  }
  _icon(icon, label, action, disabled = false, danger = false) {
    const button = document.createElement("button");
    button.className = `icon-action${danger ? " danger" : ""}`;
    button.setAttribute("aria-label", label); button.title = label; button.dataset.tooltip = label;
    button.innerHTML = `<ha-icon icon="${icon}"></ha-icon>`; button.disabled = disabled || this._busy;
    button.addEventListener("click", action); return button;
  }
  _safeCamera(value) { return String(value || "Telecamera_Blink").replace(/[^A-Za-z0-9_-]/g, "_").slice(0, 64) || "Telecamera_Blink"; }
  _fact(icon, text) {
    const node = document.createElement("span"); node.className = "storage-fact";
    const glyph = document.createElement("ha-icon"); glyph.setAttribute("icon", icon);
    const label = document.createElement("span"); label.textContent = text;
    node.append(glyph, label); return node;
  }
  _date(value) {
    const numeric = typeof value === "string" && /^\d{11,}$/.test(value) ? Number(value) : value;
    const date = new Date(numeric); return Number.isNaN(date.valueOf())
      ? (value || "Data non disponibile") : date.toLocaleString("it-IT");
  }
}

Object.assign(VistodaBlinkStorage.prototype, blinkStorageActions);

if (!customElements.get("vistoda-blink-storage")) {
  customElements.define("vistoda-blink-storage", VistodaBlinkStorage);
}
