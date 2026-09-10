import { BASE_STYLES } from "./panel-styles.js";
import { PROVIDER_RECORDING_STYLES } from "./provider-recording-styles.js";
import { recordingItem } from "./provider-recording-item.js";
import { ProviderRecordingListManager, PROVIDER_LIST_STYLES,
  PROVIDER_LIST_TEMPLATE } from "./provider-recording-list-manager.js";
import { providerRecordingActions } from "./provider-recordings-actions.js";
import { providerRecordingsTemplate } from "./provider-recordings-template.js";
import "./provider-recording-player.js";
import {
  cameraRecordings,
  recordingCommand,
} from "./provider-recording-model.js";

class VistodaProviderRecordings extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = null;
    this._items = [];
    this._pagination = { page: 1, page_size: 10, total_items: 0, total_pages: 1,
      has_previous: false, has_next: false };
    this._busy = false;
    this._selected = new Set();
    this._storage = null;
    this._listManager = new ProviderRecordingListManager(this);
    this._timer = null;
    this._mounted = false;
  }

  set hass(value) { this._hass = value; }

  connectedCallback() {
    if (!this._mounted) this._mount();
  }

  disconnectedCallback() { this._clearTimer(); }

  configure(hass, config) {
    this._hass = hass;
    const key = `${config?.provider}:${config?.entryId || ""}:${config?.alias || ""}`;
    if (key === this._key) return;
    this._key = key;
    this._config = config;
    this._items = [];
    this._selected.clear();
    this._pagination.page = 1;
    this.$?.("player")?.close();
    if (!this._mounted) this._mount();
    this._render();
    this._listManager.configure(config);
    this.reload();
  }

  _mount() {
    this._mounted = true;
    this.shadowRoot.innerHTML = providerRecordingsTemplate(
      BASE_STYLES + PROVIDER_RECORDING_STYLES + PROVIDER_LIST_STYLES, PROVIDER_LIST_TEMPLATE);
    this.$ = (id) => this.shadowRoot.getElementById(id);
    this.$("reload").addEventListener("click", () => this.reload());
    this.$("backup-all").addEventListener("click", () => this._backupAll());
    this.$("start").addEventListener("click", () => this._start());
    this.$("copy-archive-path").addEventListener("click", () => this._copyArchivePath());
    this.$("delete-selected").addEventListener("click", () => this._deleteSelected());
    this.$("previous").addEventListener("click", () => this._go(this._pagination.page - 1));
    this.$("next").addEventListener("click", () => this._go(this._pagination.page + 1));
    this._listManager.mount(this.shadowRoot);
    this._render();
  }

  async reload() {
    if (!this._config || !this._hass || this._busy) return;
    this._busy = true;
    this._render();
    try {
      const result = await this._fetch(this._pagination.page, this._pagination.page_size);
      this._items = cameraRecordings(result.recordings || [], this._config.alias);
      this._pagination = result.pagination || this._pagination;
      this._storage = result.storage || null;
      this._setMessage("");
    } catch (_error) {
      this._setMessage("Archivio temporaneamente non disponibile.");
    } finally {
      this._busy = false;
      this._render();
      this._schedule(this._items.some((item) => ["pending", "recording"].includes(item.status)));
    }
  }

  _fetch(page, pageSize) {
    return this._hass.callWS({ ...this._message("list"), page, page_size: pageSize });
  }

  async _go(page) {
    if (page < 1 || this._busy) return;
    this._pagination.page = page; this.$("player").close(); await this.reload();
  }

  _message(action) { return recordingCommand(this._config, action); }

  _render() {
    if (!this._mounted) return;
    this.$("start").disabled = this._busy || !this._config;
    this.$("reload").disabled = this._busy || !this._config;
    this.$("backup-all").disabled = this._busy || !this._config;
    const providerStorage = this.$("provider-storage");
    providerStorage.textContent = this._config?.provider === "blink"
      ? "Chiavetta Blink" : "MicroSD EZVIZ";
    this.$("destination-note").textContent = this._config?.provider === "blink"
      ? "Blink non espone una scrittura diretta e selettiva sulla chiavetta USB: il salvataggio " +
        "provider resta disabilitato finché il protocollo non è verificabile."
      : "La registrazione standalone resta separata da SceneTrove e dalla microSD della camera.";
    const directory = this._storage?.directory;
    this.$("archive-path").hidden = !directory;
    this.$("archive-directory").textContent = directory || "";
    this.$("copy-archive-path").disabled = !directory;
    this.$("summary").textContent = `Archivio locale (${this._pagination.total_items})`;
    this.$("page-label").textContent = `Pagina ${this._pagination.page} di ${this._pagination.total_pages}`;
    this.$("previous").disabled = this._busy || !this._pagination.has_previous;
    this.$("next").disabled = this._busy || !this._pagination.has_next;
    const visibleItems = this._listManager.filtered(this._items,
      (item) => `local:${item.recording_id}`);
    const nodes = visibleItems.map((item) => {
      const mediaId = `local:${item.recording_id}`;
      return recordingItem(item, {
      provider: this._config.provider, busy: this._busy,
      play: () => this._play(item), download: () => this._download(item),
      backup: () => this._backup(item), remove: () => this._delete(item),
      selected: this._selected.has(item.recording_id),
      select: (selected) => { selected ? this._selected.add(item.recording_id)
        : this._selected.delete(item.recording_id); this._render(); },
      lists: () => this._listManager.toggle(mediaId),
      tags: () => this._listManager.tags(mediaId),
      picker: this._listManager.openRecordingId === mediaId ? this._listManager.picker(mediaId) : null,
    }); });
    if (!nodes.length) {
      const empty = document.createElement("div");
      empty.className = "muted";
      empty.textContent = "Nessuna registrazione locale per questa telecamera.";
      nodes.push(empty);
    }
    this.$("list").replaceChildren(...nodes);
    this.$("bulk-actions").hidden = this._selected.size === 0;
    this.$("selected-count").textContent = `${this._selected.size} selezionate`;
    this.$("delete-selected").disabled = this._busy;
  }

  _listsChanged(resetPage) { if (resetPage) this._pagination.page = 1; this._render(); }
  _setMessage(value) { if (this.$) this.$("message").textContent = value; }
  _clearTimer() { if (this._timer) globalThis.clearTimeout(this._timer); this._timer = null; }
  _schedule(active) {
    this._clearTimer();
    if (active && this.isConnected) this._timer = globalThis.setTimeout(() => this.reload(), 2000);
  }
}
Object.assign(VistodaProviderRecordings.prototype, providerRecordingActions);
if (!customElements.get("vistoda-provider-recordings")) {
  customElements.define("vistoda-provider-recordings", VistodaProviderRecordings);
}
