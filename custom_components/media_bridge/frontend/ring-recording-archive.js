import {
  preferredRecordingView,
  recordingDate,
  recordingDuration,
  recordingPage,
  recordingSize,
  saveRecordingView,
} from "./recording-table.js";
import { copyRecordingPath, recordingInfoContent, recordingStorageSummary } from "./recording-storage.js";
import { recordingCard, recordingTableNodes } from "./ring-recording-item.js";
import { RingRecordingListManager } from "./ring-recording-list-manager.js";
import { RingRecordingPlayer } from "./ring-recording-player.js";
import { recordingArchiveTemplate } from "./ring-recording-template.js";

class RingRecordingArchive extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._recordings = [];
    this._page = 1;
    this._busy = false;
    this._infoId = null;
    this._storage = null;
    this._browserStorage = this._storageAccess();
    this._view = preferredRecordingView(
      this._browserStorage, globalThis.matchMedia?.("(max-width: 620px)").matches,
    );
    this._player = new RingRecordingPlayer(this);
    this._lists = new RingRecordingListManager(this);
  }

  configure(hass, entry) {
    const changedEntry = this._entry?.entry_id && this._entry.entry_id !== entry.entry_id;
    this._hass = hass;
    this._entry = entry;
    if (!this.shadowRoot.hasChildNodes()) this._mount();
    if (changedEntry) {
      this._player.release();
      this._recordings = [];
      this._page = 1;
      this._infoId = null;
      this._storage = null;
      this._lists.reset();
      this._lists.update([]);
    }
    this.load();
  }

  set hass(value) { this._hass = value; }
  get hass() { return this._hass; }
  get entry() { return this._entry; }
  render() { this._render(); }
  status(message) { if (this.$) this.$("status").textContent = message; }
  changed(resetPage) { if (resetPage) this._page = 1; this._render(); }

  _mount() {
    this.shadowRoot.innerHTML = recordingArchiveTemplate();
    this.$ = (id) => this.shadowRoot.getElementById(id);
    this.$("reload").addEventListener("click", () => this.load());
    this.$("delete-all").addEventListener("click", () => this._deleteAll());
    this.$("previous").addEventListener("click", () => this._changePage(-1));
    this.$("next").addEventListener("click", () => this._changePage(1));
    this.$("view-cards").addEventListener("click", () => this._setView("cards"));
    this.$("view-rows").addEventListener("click", () => this._setView("rows"));
    this._lists.mount(this.shadowRoot);
  }

  async load() {
    this._setBusy(true, "Aggiornamento archivio…");
    try {
      const result = await this._hass.callWS({
        type: "media_bridge/ring/recordings/list",
        entry_id: this._entry.entry_id,
      });
      this._storage = result.storage || null;
      this._recordings = (result.recordings || []).sort((a, b) => b.ended_at - a.ended_at);
      this._lists.update(result.lists);
      if (this._player.activeId
        && !this._recordings.some((item) => item.recording_id === this._player.activeId)) {
        this._player.release();
      }
      this.dispatchEvent(new CustomEvent("archive-changed", {
        detail: { recordings: this._recordings },
      }));
      this.status("");
    } catch (_error) {
      this.status("Impossibile caricare le registrazioni.");
    } finally {
      this._setBusy(false);
      this._render();
    }
  }

  _render() {
    if (!this.$) return;
    const filtered = this._lists.filtered(this._recordings);
    const page = recordingPage(filtered, this._page);
    this._page = page.page;
    if (this._view === "rows") {
      this.$("rows").replaceChildren(...page.items.flatMap(
        (recording) => recordingTableNodes(recording, this._context(recording)),
      ));
      this.$("cards").replaceChildren();
    } else {
      this.$("cards").replaceChildren(...page.items.map(
        (recording) => recordingCard(recording, this._context(recording)),
      ));
      this.$("rows").replaceChildren();
    }
    this.$("table-wrap").hidden = this._view !== "rows" || !filtered.length;
    this.$("cards").hidden = this._view !== "cards" || !filtered.length;
    this.$("empty").hidden = filtered.length !== 0;
    this.$("empty").textContent = this._recordings.length
      ? "Nessuna registrazione in questa lista." : "Nessuna registrazione locale.";
    this.$("pager").hidden = filtered.length === 0;
    this.$("page-label").textContent = `Pagina ${page.page} di ${page.pages}`;
    this.$("previous").disabled = this._busy || page.page === 1;
    this.$("next").disabled = this._busy || page.page === page.pages;
    this.$("delete-all").disabled = this._busy || this._recordings.length === 0;
    this.$("storage").textContent = recordingStorageSummary(this._storage);
    for (const view of ["cards", "rows"]) {
      this.$(`view-${view}`).setAttribute("aria-pressed", String(this._view === view));
    }
    this.$("view-cards").querySelector("ha-icon").setAttribute(
      "icon", this._view === "cards" ? "mdi:view-grid" : "mdi:view-grid-outline",
    );
    this.$("view-rows").querySelector("ha-icon").setAttribute(
      "icon", this._view === "rows" ? "mdi:view-list" : "mdi:view-list-outline",
    );
  }

  _context(recording) {
    return {
      date: this._date(recording), duration: recordingDuration(recording),
      size: recordingSize(recording.bytes), busy: this._busy,
      loading: this._player.loadingId === recording.recording_id,
      playerOpen: this._player.isOpen(recording.recording_id),
      infoOpen: this._infoId === recording.recording_id,
      listsOpen: this._lists.openRecordingId === recording.recording_id,
      listNames: this._lists.names(recording.recording_id), detail: this._detail(recording),
      onPlay: (item) => this._togglePlayer(item), onDelete: (item) => this._deleteOne(item),
      onInfo: (item) => this._toggleInfo(item), onLists: (item) => this._lists.toggle(item.recording_id),
    };
  }

  _detail(recording) {
    const parts = [];
    if (this._player.isOpen(recording.recording_id)) parts.push(this._player.detail(recording));
    if (this._infoId === recording.recording_id) {
      const info = recordingInfoContent(recording, this._storage);
      info.addEventListener("copy-path", (event) => this._copyPath(event.detail.path));
      parts.push(info);
    }
    if (this._lists.openRecordingId === recording.recording_id) {
      parts.push(this._lists.picker(recording));
    }
    if (!parts.length) return null;
    const detail = document.createElement("div");
    detail.className = "recording-details";
    detail.append(...parts);
    return detail;
  }

  _toggleInfo(recording) {
    this._infoId = this._infoId === recording.recording_id ? null : recording.recording_id;
    this._render();
  }

  _togglePlayer(recording) {
    if (this._player.isOpen(recording.recording_id)) this._player.close();
    else this._player.play(recording);
  }

  _setView(view) {
    this._view = view;
    saveRecordingView(this._browserStorage, view);
    this._render();
  }

  async _deleteOne(recording) {
    if (!window.confirm(`Eliminare la registrazione del ${this._date(recording)}?`)) return;
    if (this._player.activeId === recording.recording_id) this._player.release();
    await this._delete("media_bridge/ring/recordings/delete", {
      recording_id: recording.recording_id,
    }, "Registrazione eliminata.");
  }

  async _deleteAll() {
    const count = this._recordings.length;
    if (!window.confirm(`Eliminare definitivamente tutte le ${count} registrazioni?`)) return;
    this._player.release();
    await this._delete(
      "media_bridge/ring/recordings/delete_all", {}, `${count} registrazioni eliminate.`,
    );
  }

  async _delete(type, payload, success) {
    this._setBusy(true, "Eliminazione in corso…");
    try {
      const result = await this._hass.callWS({
        type, entry_id: this._entry.entry_id, ...payload,
      });
      await this.load();
      this.status(result.failed
        ? `${result.deleted} eliminate, ${result.failed} non eliminate.` : success);
    } catch (_error) {
      this.status("Eliminazione non riuscita.");
    } finally {
      this._setBusy(false);
      this._render();
    }
  }

  _setBusy(busy, message = "") {
    this._busy = busy;
    if (this.$) {
      this.$("reload").disabled = busy;
      if (message) this.status(message);
    }
  }

  _changePage(step) { this._page += step; this._render(); }
  async _copyPath(path) {
    this.status(await copyRecordingPath(path)
      ? "Percorso copiato." : "Impossibile copiare il percorso.");
  }
  _date(recording) {
    return recordingDate(recording, this._hass?.locale?.language, this._hass?.config?.time_zone);
  }
  _storageAccess() {
    try { return globalThis.localStorage; } catch (_error) { return null; }
  }

  disconnectedCallback() { this._player.release(); }
}

if (!customElements.get("vistoda-ring-recording-archive")) {
  customElements.define("vistoda-ring-recording-archive", RingRecordingArchive);
}
