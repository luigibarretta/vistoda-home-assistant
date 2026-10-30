// Modal for one EZVIZ event: large picture, time, category and title,
// previous/next event, and the video of that moment — a ready recording that
// covers it, else saving that minute from the microSD (which wakes the camera).
import { copy, localizeCopy } from "./panel-copy.js";
import { alarmIsoTime, alarmTimeText, alarmVideo, navigationStep } from "./ezviz-alarm-model.js";
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
  @media (max-width:600px){dialog{width:100vw;max-width:none;height:100dvh;max-height:none;border-radius:0}}`;

class VistodaEzvizAlarmDialog extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this.shadowRoot.innerHTML = `<style>${STYLE}</style><dialog id="dialog" aria-labelledby="title">
      <div class="bar"><button id="previous"><ha-icon icon="mdi:chevron-left"></ha-icon></button>
        <h2 id="title"></h2><button id="next"><ha-icon icon="mdi:chevron-right"></ha-icon></button>
        <button id="close"><ha-icon icon="mdi:close"></ha-icon></button></div>
      <img id="picture" alt="" hidden><div class="meta"><time id="time"></time><div id="subtitle" class="muted"></div></div>
      <section class="video"><h3 id="video-title"></h3><div id="video"></div><p id="status" class="muted" role="status"></p>
        <vistoda-provider-recording-player id="player" hidden></vistoda-provider-recording-player></section></dialog>`;
    this.$ = (id) => this.shadowRoot.getElementById(id);
    this.$("close").addEventListener("click", () => this.$("dialog").close());
    this.$("previous").addEventListener("click", () => this._show(this._index - 1));
    this.$("next").addEventListener("click", () => this._show(this._index + 1));
    this.$("dialog").addEventListener("close", () => this.$("player").close());
    this.$("dialog").addEventListener("keydown", (event) => {
      const step = navigationStep(event.key, event.composedPath());
      if (step) this._show(this._index + step);
    });
  }

  // rows: card rows (newest first); index: the tapped one.
  open(hass, { entryId, alias, rows, index }) {
    Object.assign(this, { _hass: hass, _entryId: entryId, _alias: alias, _rows: rows, _recordings: null });
    for (const [id, label] of [["previous", "Evento precedente"], ["next", "Evento successivo"], ["close", "Chiudi"]]) {
      this.$(id).setAttribute("aria-label", copy(this, label));
    }
    this.$("video-title").textContent = copy(this, "Video");
    localizeCopy(this.shadowRoot, this);
    this.$("dialog").showModal();
    this._show(index);
  }

  async _show(index) {
    if (!this._rows?.[index]) return;
    const row = this._rows[index];
    const shown = (this._index = index);
    const locale = this._hass?.locale?.language || "it-IT";
    this.$("previous").disabled = index <= 0;
    this.$("next").disabled = index >= this._rows.length - 1;
    this.$("title").textContent = copy(this, row.label);
    this.$("time").dateTime = alarmIsoTime(row.occurredAt);
    this.$("time").textContent = alarmTimeText(row.occurredAt, locale);
    this.$("subtitle").textContent = row.title;
    this.$("player").close();
    this.$("status").textContent = "";
    this.$("video").textContent = copy(this, "Caricamento…");
    this.$("picture").hidden = true;
    if (row.picture) this._picture(row, shown);
    const video = alarmVideo(await this._loadRecordings(), row.occurredAt);
    if (shown === this._index) this._renderVideo(video);
  }

  async _picture(row, shown) {
    try {
      const signed = await this._hass.callWS({ type: "auth/sign_path", path: row.picture, expires: 900 });
      if (shown !== this._index) return;
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
    const button = this._action("mdi:content-save-outline", copy(this, "Salva dalla microSD"));
    const hint = Object.assign(document.createElement("p"), {
      className: "muted", textContent: copy(this, "Sveglia la telecamera e consuma batteria."),
    });
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
      }[error?.code] || "Impossibile salvare la clip.");
      button.disabled = false;
    }
  }
}

if (!customElements.get("vistoda-ezviz-alarm-dialog")) {
  customElements.define("vistoda-ezviz-alarm-dialog", VistodaEzvizAlarmDialog);
}
