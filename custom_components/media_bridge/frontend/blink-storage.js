import { copy, localizeCopy } from "./panel-copy.js";
import { BASE_STYLES } from "./panel-styles.js";
import { BLINK_STORAGE_STYLES } from "./blink-storage-styles.js";
import { ProviderRecordingListManager } from "./provider-recording-list-manager.js";
import { PROVIDER_LIST_STYLES, PROVIDER_LIST_TEMPLATE } from "./provider-recording-list-template.js";
import { ProviderRecordingBulkLists, PROVIDER_BULK_LIST_STYLES,
  PROVIDER_BULK_LIST_TEMPLATE } from "./provider-recording-bulk-lists.js";
import { blinkStorageActions } from "./blink-storage-actions.js";
import { blinkStorageUi } from "./blink-storage-ui.js";
import { blinkStorageTemplate } from "./blink-storage-template.js";
import { bindPageSize, renderPageSize } from "./archive-page-size.js";
import { MobileCardSelection } from "./mobile-card-selection.js";

class VistodaBlinkStorage extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._storages = []; this._busy = false; this._loaded = false;
    this._page = 1; this._pageSize = 10; this._selected = new Set();
    this._listManager = new ProviderRecordingListManager(this);
    this._bulkListManager = new ProviderRecordingBulkLists(this, this._listManager,
      () => [...this._selected].map((id) => `usb:${id}`));
    this._mount();
  }

  set hass(value) { this.configure(value, this._config); }

  configure(hass, config) {
    this._hass = hass; this._config = config;
    this._render();
    this._listManager.configure(config);
    if (hass && !this._loaded && !this._busy) this.reload();
  }

  _mount() {
    this.shadowRoot.innerHTML = blinkStorageTemplate(
      BASE_STYLES + BLINK_STORAGE_STYLES + PROVIDER_LIST_STYLES + PROVIDER_BULK_LIST_STYLES,
      PROVIDER_LIST_TEMPLATE, PROVIDER_BULK_LIST_TEMPLATE); localizeCopy(this.shadowRoot, this);
    this.$ = (id) => this.shadowRoot.getElementById(id);
    this.$("reload").addEventListener("click", () => this.reload());
    bindPageSize(this.shadowRoot, async (size) => {
      if (this._busy) return;
      this._pageSize = size; await this._go(1);
    });
    this.$("backup-all").addEventListener("click", () => this._backupAll());
    this.$("close-player").addEventListener("click", () => this._closePlayer());
    this.$("delete-selected").addEventListener("click", () => this._deleteSelected());
    this.$("selection-mode").addEventListener("click", () =>
      this._selection.setMode(!this._selection.mode));
    this.$("format-confirmation").addEventListener("input", () => {
      this.$("confirm-format").disabled = this.$("format-confirmation").value !== this._formatPhrase;
    });
    this.$("format-dialog").addEventListener("close", () => {
      if (this.$("format-dialog").returnValue === "confirm") this._format();
    });
    this._listManager.mount(this.shadowRoot);
    this._bulkListManager.mount(this.shadowRoot);
    this._selection = new MobileCardSelection(this.shadowRoot, ".clip[data-selection-key]", {
      selected: (key) => this._selected.has(key),
      select: (key, selected) => this._select(key, selected), render: () => this._render(),
    });
    this._render();
  }

  async _fetch(page, pageSize = this._pageSize) {
    return this._hass.callWS({ type: "blink_live_bridge/local_storage/list",
      page, page_size: pageSize });
  }

  async reload() {
    if (!this._hass || this._busy) return;
    this._busy = true; this._setMessage(copy(this, "Lettura indice USB Blink…")); this._render();
    try {
      const result = await this._fetch(this._page);
      this._storages = Array.isArray(result.storages) ? result.storages : [];
      this._loaded = true; this._setMessage("");
    } catch (_error) {
      this._setMessage(copy(this, "Archivio USB non disponibile o Sync Module senza supporto."));
    } finally { this._busy = false; this._render(); }
  }

  _render() {
    if (localizeCopy(this.shadowRoot, this)) this._listManager.update(this._listManager.lists);
    this.$("reload").disabled = this._busy || !this._hass;
    renderPageSize(this.shadowRoot, this._pageSize, this._busy, this._hass?.locale?.language);
    this.$("backup-all").disabled = this._busy || !this._hass;
    const nodes = this._storages.map((storage) => this._module(storage));
    if (!nodes.length && this._loaded) {
      const empty = document.createElement("div"); empty.className = "muted";
      empty.textContent = copy(this, "Nessuna chiavetta USB Blink disponibile."); nodes.push(empty);
    }
    this.$("content").replaceChildren(...nodes);
    const total = this._storages.reduce((sum, storage) => sum + (storage.pagination?.total_items || 0), 0);
    this.$("selected-count").textContent = copy(this, "{p0} clip · {p1} selezionate", {
      p0: total, p1: this._selected.size,
    });
    this.$("selection-mode").disabled = this._busy || !total;
    this.$("selection-mode").setAttribute("aria-pressed", String(Boolean(this._selection?.mode)));
    this.$("delete-selected").disabled = this._busy || !this._selectedDeletable();
    this.$("add-selected-to-lists").disabled = this._busy || !this._selected.size;
  }

  _module(storage) {
    const details = document.createElement("details"); details.className = "module"; details.open = true;
    const summary = document.createElement("summary");
    const title = document.createElement("strong"); title.textContent = storage.network_name || copy(this, "Sistema Blink");
    const count = document.createElement("span");
    count.textContent = copy(this, "{p0} clip", { p0: storage.pagination?.total_items ?? storage.clips?.length ?? 0 });
    summary.append(title, count);
    const body = document.createElement("div"); body.className = "module-body";
    const sync = document.createElement("section"); sync.className = "sync-module-info";
    const syncIcon = document.createElement("ha-icon");
    const online = ["online", "active", "available"].includes(String(storage.sync_module_status || "").toLowerCase());
    syncIcon.setAttribute("icon", online ? "mdi:wifi" : "mdi:wifi-off");
    const syncText = document.createElement("div"); const syncTitle = document.createElement("strong");
    syncTitle.textContent = copy(this, online ? "Sync Module online" : "Stato Sync Module non confermato");
    const firmware = document.createElement("small"); firmware.textContent = copy(this,
      "Firmware: {p0}", { p0: storage.sync_module_firmware || "—" });
    syncText.append(syncTitle, firmware); sync.append(syncIcon, syncText);
    const facts = document.createElement("div"); facts.className = "module-facts";
    facts.append(this._fact("mdi:usb-flash-drive", copy(this, "Stato USB"),
      storage.status?.usb_state || copy(this, "stato sconosciuto")));
    const used = Number.isFinite(storage.status?.usb_storage_used)
      ? storage.status.usb_storage_used
      : Number.isFinite(storage.status?.usb_storage_available_percentage)
        ? 100 - storage.status.usb_storage_available_percentage : null;
    if (Number.isFinite(used)) {
      facts.append(this._storageGauge(used));
    }
    if (storage.status?.last_backup_completed) {
      facts.append(this._fact("mdi:cloud-check-outline", copy(this, "Ultimo backup Blink"),
        this._date(storage.status.last_backup_completed)));
    }
    if (storage.status?.can_format_usb) {
      const format = this._icon("mdi:format-page-break", copy(this, "Formatta chiavetta"),
        () => this._openFormat(storage), false, true);
      format.classList.add("format-action"); format.removeAttribute("title"); facts.append(format);
    }
    const moduleActions = document.createElement("div"); moduleActions.className = "module-actions";
    moduleActions.append(this._moduleAction("mdi:wifi-cog", copy(this, "Cambia rete Wi-Fi"),
      copy(this, "Procedura non ancora verificata: usa l’app Blink.")),
    this._moduleAction("mdi:eject-outline", copy(this, "Espelli in sicurezza"),
      copy(this, "Espulsione non ancora verificata: usa l’app Blink.")),
    this._moduleAction("mdi:delete-outline", copy(this, "Elimina Sync Module"),
      copy(this, "Rimozione non disponibile in Vistoda per proteggere la configurazione."), true));
    const clips = this._listManager.filtered(storage.clips || [], (clip) => this._mediaId(storage, clip));
    const rows = clips.map((clip) => this._clip(storage, clip));
    if (!rows.length) {
      const empty = document.createElement("div"); empty.className = "muted";
      empty.textContent = this._listManager.filterId
        ? copy(this, "Nessuna clip di questa pagina appartiene alla lista.") : copy(this, "Nessuna clip indicizzata in questa pagina.");
      rows.push(empty);
    }
    body.append(sync, facts, moduleActions, ...rows, this._pager(storage.pagination));
    details.append(summary, body); return details;
  }

  _clip(storage, clip) {
    const row = document.createElement("article"); row.className = "clip";
    const key = this._selectionKey(storage, clip); const mediaId = this._mediaId(storage, clip);
    row.dataset.selectionKey = key; row.setAttribute("aria-selected", String(this._selected.has(key)));
    const selector = document.createElement("label"); selector.className = "select-clip";
    const checkbox = document.createElement("input"); checkbox.type = "checkbox";
    checkbox.checked = this._selected.has(key); checkbox.disabled = this._busy;
    checkbox.setAttribute("aria-label", copy(this, "Seleziona clip {p0}", { p0: clip.device_name || clip.id }));
    checkbox.addEventListener("change", () => this._select(key, checkbox.checked)); selector.append(checkbox);
    const text = document.createElement("div"); const title = document.createElement("strong");
    title.textContent = clip.device_name || copy(this, "Telecamera Blink");
    const meta = document.createElement("small"); const duration = Number.isFinite(clip.clip_length_ms)
      ? ` · ${(clip.clip_length_ms / 1000).toFixed(1)} s` : "";
    meta.textContent = `${this._date(clip.created_at)}${duration}`; text.append(title, meta);
    const tags = this._listManager.tags(mediaId); if (tags) text.append(tags);
    const actions = document.createElement("div"); actions.className = "clip-actions";
    actions.append(this._icon("mdi:play", copy(this, "Riproduci"), () => this._play(storage, clip), !clip.media_available));
    actions.append(this._icon("mdi:download", copy(this, "Scarica"), () => this._download(storage, clip), !clip.media_available));
    actions.append(this._icon("mdi:cloud-upload", copy(this, "Backup NFS"), () => this._backupSingle(storage, clip), !clip.media_available));
    actions.append(this._icon("mdi:playlist-plus", copy(this, "Aggiungi alle liste"),
      () => this._listManager.toggle(mediaId), false));
    actions.append(this._icon("mdi:delete-outline", copy(this, "Elimina clip"),
      () => this._deleteOne(storage, clip), !storage.status?.can_delete_clips, true));
    row.append(selector, text, actions);
    if (this._listManager.openRecordingId === mediaId) row.append(this._listManager.picker(mediaId));
    return row;
  }

  _pager(pagination = {}) {
    const pager = document.createElement("nav"); pager.className = "archive-pager";
    pager.setAttribute("aria-label", copy(this, "Pagine archivio Blink"));
    const previous = this._button("mdi:chevron-left", copy(this, "Precedente"),
      () => this._go(pagination.page - 1), !pagination.has_previous);
    const label = document.createElement("span");
    label.textContent = copy(this, "Pagina {p0} di {p1}", { p0: pagination.page || 1, p1: pagination.total_pages || 1 });
    const next = this._button("mdi:chevron-right", copy(this, "Successiva"),
      () => this._go(pagination.page + 1), !pagination.has_next);
    pager.append(previous, label, next); return pager;
  }

  async _go(page) {
    if (page < 1 || this._busy) return;
    this._page = page; this._selected.clear(); this._closePlayer(); await this.reload();
  }

  _selectionKey(storage, clip) { return `${storage.network_id}:${storage.sync_module_id}:${storage.manifest_id}:${clip.id}`; }
  _mediaId(storage, clip) { return `usb:${this._selectionKey(storage, clip)}`; }
  _selectedDeletable() {
    for (const storage of this._storages) for (const clip of storage.clips || []) {
      if (this._selected.has(this._selectionKey(storage, clip)) && !storage.status?.can_delete_clips) return false;
    }
    return true;
  }
  _bulkListsApplied() { this._selected.clear(); this._render(); }
  _select(key, selected) { selected ? this._selected.add(key) : this._selected.delete(key); this._render(); }
  _listsChanged(resetPage) {
    if (resetPage) { this._page = 1; this._selected.clear(); }
    this._render();
  }
  _setMessage(value) { if (this.$) this.$("status").textContent = value; }
  _button(icon, label, action, disabled = false) {
    const button = document.createElement("button");
    button.innerHTML = `<ha-icon icon="${icon}"></ha-icon><span>${label}</span>`; localizeCopy(button, this);
    button.disabled = disabled || this._busy; button.addEventListener("click", action); return button;
  }
  _icon(icon, label, action, disabled = false, danger = false) {
    const button = document.createElement("button");
    button.className = `icon-action${danger ? " danger" : ""}`;
    button.setAttribute("aria-label", label); button.title = label; button.dataset.tooltip = label;
    button.innerHTML = `<ha-icon icon="${icon}"></ha-icon>`; localizeCopy(button, this); button.disabled = disabled || this._busy;
    button.addEventListener("click", action); return button;
  }
  _safeCamera(value) { return String(value || "Telecamera_Blink").replace(/[^A-Za-z0-9_-]/g, "_").slice(0, 64) || "Telecamera_Blink"; }
  _date(value) {
    const numeric = typeof value === "string" && /^\d{11,}$/.test(value) ? Number(value) : value;
    const date = new Date(numeric); return Number.isNaN(date.valueOf())
      ? (value || copy(this, "Data non disponibile")) : date.toLocaleString(this._hass?.locale?.language || "en");
  }
}

Object.assign(VistodaBlinkStorage.prototype, blinkStorageActions, blinkStorageUi);

if (!customElements.get("vistoda-blink-storage")) {
  customElements.define("vistoda-blink-storage", VistodaBlinkStorage);
}
