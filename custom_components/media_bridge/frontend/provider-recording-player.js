import { copy, localizeCopy } from "./panel-copy.js";
import { recordingMediaPath } from "./provider-recording-model.js";
import { BASE_STYLES } from "./panel-styles.js";

class VistodaProviderRecordingPlayer extends HTMLElement {
  constructor() {
    super(); this.attachShadow({ mode: "open" }); this._generation = 0;
    this.shadowRoot.innerHTML = `<style>${BASE_STYLES}
      :host { display:block; margin:12px 0; } :host([hidden]) { display:none !important; }
      section { padding:12px; border:1px solid var(--divider-color); border-radius:14px;
        background:var(--secondary-background-color); }
      header { display:flex; align-items:center; justify-content:space-between; gap:10px;
        margin-bottom:10px; }
      video { display:block; width:100%; max-height:62vh; border-radius:12px; background:#000; }
      button { min-height:40px; padding:7px 12px; border:1px solid var(--divider-color);
        display:inline-flex; align-items:center; justify-content:center; gap:6px;
        border-radius:10px; color:var(--primary-text-color); background:var(--card-background-color);
        cursor:pointer; }
      button ha-icon { --mdc-icon-size:19px; }
      .message { margin-top:8px; color:var(--secondary-text-color); font-size:12px; }
    </style><section><header><strong id="title"><span data-copy="Riproduzione registrazione">Riproduzione registrazione</span></strong>
      <button id="close"><ha-icon icon="mdi:close"></ha-icon>
      <span><span data-copy="Chiudi riproduzione">Chiudi riproduzione</span></span></button></header>
      <video id="video" controls playsinline preload="metadata"></video>
      <div class="message" id="message" role="status"></div></section>`; localizeCopy(this.shadowRoot, this);
    this.$ = (id) => this.shadowRoot.getElementById(id);
    this.$("close").addEventListener("click", () => this.close());
    this.$("video").addEventListener("error", () => {
      this.$("message").textContent = copy(this, "Il browser non riesce a riprodurre questa registrazione.");
    });
    this.hidden = true;
  }

  async open(hass, config, item) {
    this._hass = hass; localizeCopy(this.shadowRoot, this);
    this.close();
    const generation = this._generation;
    const path = recordingMediaPath(config, item.recording_id, true);
    const signed = await hass.callWS({ type: "auth/sign_path", path, expires: 900 });
    if (generation !== this._generation) return false;
    this.$("title").textContent = new Date(item.started_at || item.requested_at)
      .toLocaleString(hass?.locale?.language || "en");
    this.$("video").src = hass.hassUrl(signed.path); this.hidden = false;
    this.$("video").load(); this.scrollIntoView({ behavior: "smooth", block: "nearest" });
    return true;
  }

  close() {
    this._generation += 1;
    const video = this.$("video"); video.pause(); video.removeAttribute("src"); video.load();
    this.$("message").textContent = ""; this.hidden = true;
  }
}

if (!customElements.get("vistoda-provider-recording-player")) {
  customElements.define("vistoda-provider-recording-player", VistodaProviderRecordingPlayer);
}
