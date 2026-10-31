// Modal for one EZVIZ event: large picture, time, category and title,
// previous/next event, and the video of that moment — a ready recording that
// covers it, else saving that minute from the microSD (which wakes the camera).
import { copy, localizeCopy } from "./panel-copy.js";
import {
  alarmIsoTime, alarmTimeText, alarmVideo, archivedEventName, deleteEventPrompt, navigationStep, neighbour, sceneTroveLink,
} from "./ezviz-alarm-model.js";
import "./provider-recording-player.js";

const STYLE = `
  dialog{border:0;border-radius:16px;padding:0;width:min(720px,calc(100vw - 32px));max-height:calc(100dvh - 32px);
    background:var(--card-background-color,#1c1c1c);color:var(--primary-text-color)}
  dialog::backdrop{background:#000a}
  .bar{display:flex;align-items:center;gap:4px;padding:8px}.bar h2{flex:1;margin:0 8px;font-size:17px}
  button{min-width:44px;min-height:44px;border:0;border-radius:12px;background:transparent;color:inherit;cursor:pointer}
  button:focus-visible{outline:2px solid var(--primary-color);outline-offset:2px}button:disabled{opacity:.45;cursor:not-allowed}
  img{display:block;width:100%;max-height:60dvh;object-fit:contain;background:#000}
  .meta{padding:12px 16px}.meta time,.muted{color:var(--secondary-text-color);font-size:13px}
  .video{padding:0 16px 16px}.video h3{margin:8px 0;font-size:15px}
  .action{display:inline-flex;align-items:center;gap:6px;padding:0 14px;background:var(--primary-color);color:var(--text-primary-color,#fff)}
  a.action{min-height:44px;margin-bottom:8px;border-radius:12px;text-decoration:none}.action[hidden]{display:none}
  @media (max-width:600px){dialog{width:100vw;max-width:none;height:100dvh;max-height:none;border-radius:0}}`;

class VistodaEzvizAlarmDialog extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this.shadowRoot.innerHTML = `<style>${STYLE}</style><dialog id="dialog" aria-labelledby="title">
      <div class="bar"><button id="previous"><ha-icon icon="mdi:chevron-left"></ha-icon></button>
        <h2 id="title"></h2><button id="next"><ha-icon icon="mdi:chevron-right"></ha-icon></button>
        <button id="close" autofocus><ha-icon icon="mdi:close"></ha-icon></button></div>
      <img id="picture" alt="" hidden><div class="meta"><time id="time"></time><div id="subtitle" class="muted"></div>
        <button id="delete" hidden><ha-icon icon="mdi:delete-outline"></ha-icon></button></div>
      <section class="video"><a id="scenetrove" class="action" target="_blank" rel="noopener" hidden>
        <ha-icon icon="mdi:open-in-new"></ha-icon><span data-copy="Apri in SceneTrove">Apri in SceneTrove</span></a>
        <h3 id="video-title"></h3><div id="video"></div><p id="status" class="muted" role="status"></p>
        <vistoda-provider-recording-player id="player" hidden></vistoda-provider-recording-player></section></dialog>`;
    this.$ = (id) => this.shadowRoot.getElementById(id);
    this.$("close").addEventListener("click", () => this.$("dialog").close());
    this.$("previous").addEventListener("click", () => this._move(-1));
    this.$("delete").addEventListener("click", () => this._delete());
    this.$("next").addEventListener("click", () => this._move(1));
    this.$("dialog").addEventListener("close", () => this.$("player").close());
    this.$("dialog").addEventListener("keydown", (event) => {
      const step = navigationStep(event.key, event.composedPath());
      if (step) this._move(step);
    });
  }

  // rows: card rows (newest first); index: the tapped one; pager: the card's
  // page loader, so the modal can step past the first or last row of a page;
  // sceneTrove: the linked SceneTrove `{ url, device, shared }`, when set;
  // archived: the rows come from the event archive, so administrators may delete them.
  open(hass, { entryId, alias, rows, index, pager = null, sceneTrove = null, archived = false }) {
    Object.assign(this, { _hass: hass, _entryId: entryId, _alias: alias, _rows: rows, _pager: pager, _recordings: null, _archived: null });
    Object.assign(this, { _sceneTrove: sceneTrove, _deletable: archived && Boolean(hass?.user?.is_admin) });
    this.$("delete").hidden = !this._deletable;
    this._opened = (this._opened || 0) + 1; // late answers of an earlier opening are ignored
    for (const [id, label] of [["previous", "Evento più recente"], ["next", "Evento più vecchio"], ["close", "Chiudi"], ["delete", "Elimina evento"]]) {
      this.$(id).setAttribute("aria-label", copy(this, label));
    }
    this.$("video-title").textContent = copy(this, "Video");
    localizeCopy(this.shadowRoot, this);
    this.$("dialog").showModal();
    // The panel keeps focus on the page after the tap; move it into the modal so
    // keyboard users (and the arrow keys) start inside it.
    this.$("close").focus({ preventScroll: true });
    this._show(index);
  }

  _current() {
    return `${this._opened}:${this._index}`;
  }

  async _move(step) {
    const target = neighbour(this._index, this._rows.length, step);
    if (target.index !== undefined) return this._show(target.index);
    if (!this._pager?.has(target.page)) return;
    const rows = await this._pager.load(target.page);
    if (!rows?.length) return;
    this._rows = rows;
    this._show(step > 0 ? 0 : rows.length - 1);
  }

  _edge(step) {
    const target = neighbour(this._index, this._rows.length, step);
    return target.index === undefined && !this._pager?.has(target.page);
  }

  async _show(index) {
    if (!this._rows?.[index]) return;
    const row = this._rows[index];
    this._index = index;
    const shown = this._current();
    const locale = this._hass?.locale?.language || "it-IT";
    this.$("previous").disabled = this._edge(-1);
    this.$("next").disabled = this._edge(1);
    this.$("title").textContent = copy(this, row.label);
    this.$("time").dateTime = alarmIsoTime(row.occurredAt);
    this.$("time").textContent = alarmTimeText(row.occurredAt, locale);
    this.$("subtitle").textContent = row.title;
    const link = sceneTroveLink(this._sceneTrove?.url, this._sceneTrove?.device, row.occurredAt);
    if (link) this.$("scenetrove").href = link;
    else this.$("scenetrove").removeAttribute("href");
    this.$("scenetrove").hidden = !link;
    this.$("player").close();
    this.$("status").textContent = "";
    this.$("video").textContent = copy(this, "Caricamento…");
    this.$("picture").hidden = true;
    if (row.picture) this._picture(row, shown);
    const [recordings, archived] = await Promise.all([this._loadRecordings(), this._loadArchived()]);
    const video = alarmVideo(recordings, row.occurredAt, Date.now() / 1000, archived);
    if (shown === this._current()) this._renderVideo(video);
  }

  async _picture(row, shown) {
    try {
      const signed = await this._hass.callWS({ type: "auth/sign_path", path: row.picture, expires: 900 });
      if (shown !== this._current()) return;
      Object.assign(this.$("picture"), { src: this._hass.hassUrl(signed.path), hidden: false,
        alt: copy(this, "Immagine evento: {p0}", { p0: copy(this, row.label) }) });
    } catch { /* The event keeps its text without a picture. */ }
  }

  async _loadRecordings() {
    this._recordings ??= this._hass.callWS({
      type: "media_bridge/ezviz/recordings/list", entry_id: this._entryId, page: 1, page_size: 100,
    }).then((result) => result?.recordings || [], () => []);
    return this._recordings;
  }

  // Network archive copies of this camera; the inventory is administrator-only.
  async _loadArchived() {
    if (!this._hass?.user?.is_admin) return [];
    this._archived ??= this._hass.callWS({
      type: "media_bridge/network_archive/list", entry_id: this._entryId, camera: this._alias, page_size: 100,
    }).then((result) => result?.items || [], () => []);
    return this._archived;
  }

  async _delete() {
    const row = this._rows[this._index];
    if (!row || !globalThis.confirm(copy(this, deleteEventPrompt(Boolean(this._sceneTrove?.shared))))) return;
    try {
      const result = await this._hass.callWS({
        type: "media_bridge/events/delete", entry_id: this._entryId, ids: [archivedEventName(row)],
      });
      if (result?.deleted !== 1) throw new Error("not deleted");
      this.dispatchEvent(new CustomEvent("alarm-deleted", { bubbles: true, composed: true }));
      this.$("dialog").close();
    } catch {
      this.$("status").textContent = copy(this, "Eliminazione non riuscita.");
    }
  }

  async _download(item) {
    try {
      const signed = await this._hass.callWS({ type: "auth/sign_path", path: item.media_path, expires: 300 });
      const link = Object.assign(document.createElement("a"), {
        href: this._hass.hassUrl(signed.path), download: item.id.split("/").pop(),
      });
      link.click();
    } catch {
      this.$("status").textContent = copy(this, "Download non disponibile.");
    }
  }

  _action(icon, label) {
    const button = Object.assign(document.createElement("button"), { className: "action" });
    const symbol = document.createElement("ha-icon");
    symbol.setAttribute("icon", icon);
    button.append(symbol, label);
    return button;
  }

  _renderVideo(video) {
    const target = this.$("video");
    if (video.kind === "play") {
      const button = this._action("mdi:play", copy(this, "Riproduci la registrazione"));
      button.addEventListener("click", () => this.$("player").open(
        this._hass, { provider: "ezviz", entryId: this._entryId, alias: this._alias }, video.recording));
      target.replaceChildren(button);
      return;
    }
    if (video.kind === "download") {
      const button = this._action("mdi:download", copy(this, "Scarica la copia archiviata"));
      button.addEventListener("click", () => this._download(video.item));
      target.replaceChildren(button);
      return;
    }
    const button = this._action("mdi:content-save-outline", copy(this, "Salva dalla microSD"));
    const hint = Object.assign(document.createElement("p"), {
      className: "muted", textContent: copy(this, "Sveglia la telecamera e consuma batteria."),
    });
    if (video.kind === "wait") {
      target.textContent = copy(this, "Evento appena avvenuto: riprova tra qualche secondo.");
      return;
    }
    if (!this._hass?.user?.is_admin) {
      target.textContent = copy(this, "Solo un amministratore può salvare dalla microSD.");
      return;
    }
    button.addEventListener("click", () => this._save(video, button));
    target.replaceChildren(button, hint);
  }

  async _save(video, button) {
    button.disabled = true;
    this.$("status").textContent = copy(this, "Salvataggio della clip…");
    try {
      await this._hass.callWS({ type: "media_bridge/ezviz/recordings/create_sd", entry_id: this._entryId,
        start: video.start, end: video.end, request_id: globalThis.crypto.randomUUID() });
      this.$("status").textContent = copy(this, "Clip in salvataggio: comparirà nelle registrazioni locali.");
      this._recordings = null;
    } catch (error) {
      this.$("status").textContent = copy(this, {
        live_active: "Chiudi il live per salvare la clip.",
        conflict: "Un’altra registrazione di questa telecamera è in corso.",
        unauthorized: "Solo un amministratore può salvare dalla microSD.",
      }[error?.code] || "Impossibile salvare la clip.");
      button.disabled = false;
    }
  }
}

if (!customElements.get("vistoda-ezviz-alarm-dialog")) {
  customElements.define("vistoda-ezviz-alarm-dialog", VistodaEzvizAlarmDialog);
}
