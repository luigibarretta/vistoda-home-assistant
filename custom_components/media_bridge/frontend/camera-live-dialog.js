import { loadHaCardHelpers } from "./ha-card-helpers.js";
import { LiveRotation } from "./live-rotation.js";
import { findLiveVideo } from "./live-fullscreen.js";
import { copy } from "./panel-copy.js";
import { setPlayerMuted } from "./live-speaker.js";

// Provider-neutral, user-opened viewer. Removing the card releases its HA stream.
export class CameraLiveDialog {
  constructor(host) { this.host = host; this.generation = 0; }
  async open(hass, entityId) {
    this.close();
    if (!entityId?.startsWith("camera.")) return;
    const generation = ++this.generation;
    const doc = this.host.ownerDocument;
    const dialog = doc.createElement("dialog"); this.dialog = dialog;
    dialog.setAttribute("aria-label", hass.states[entityId]?.attributes.friendly_name || "Live");
    dialog.style.cssText = "margin:0;padding:0;border:0;width:100vw;max-width:none;height:100dvh;max-height:none;background:#000;color:white";
    const container = doc.createElement("div"); container.style.height = "100%";
    dialog.append(container);
    const root = container.attachShadow({ mode: "open" });
    root.innerHTML = `<style>
      #stage { width:100%;height:100%;position:relative;overflow:hidden;background:#000; }
      #media { position:absolute;inset:0;display:flex;align-items:center;justify-content:center; }
      #media > * { width:100%; }
      nav { position:absolute;z-index:3;right:12px;top:max(12px,env(safe-area-inset-top));display:flex;gap:8px; }
      button { width:44px;height:44px;border:1px solid #888;border-radius:50%;background:#181818;color:#fff;cursor:pointer; }
      button:focus-visible { outline:3px solid #00bcd4;outline-offset:2px; }
      #loading { position:absolute;inset:0;z-index:2;background:#000;display:grid;place-items:center; }
      #loading[hidden] { display:none; }
      #loading::after { content:"";width:40px;height:40px;border:4px solid #555;border-top-color:#fff;border-radius:50%;animation:spin 1s linear infinite; }
      @keyframes spin { to { transform:rotate(360deg); } }
      @media(prefers-reduced-motion:reduce) { #loading::after { animation:none; } }
      #status { position:absolute;bottom:16px;left:16px;right:16px;z-index:3;color:#fff; }
    </style><div id="stage"><div id="media"></div><div id="loading" aria-hidden="true"></div>
      <nav><button id="speaker"><ha-icon icon="mdi:volume-off"></ha-icon></button>
      <button id="rotate" aria-pressed="false"><ha-icon icon="mdi:screen-rotation"></ha-icon></button>
      <button id="close"><ha-icon icon="mdi:close"></ha-icon></button></nav><p id="status" role="status"></p></div>`;
    const get = (id) => root.getElementById(id);
    for (const [id, text] of [["speaker", "Attiva audio"], ["rotate", "Ruota visualizzazione"], ["close", "Chiudi live"]]) {
      get(id).title = copy({ hass }, text); get(id).setAttribute("aria-label", copy({ hass }, text));
    }
    get("close").onclick = () => this.close();
    dialog.addEventListener("cancel", (event) => { event.preventDefault(); this.close(); });
    this.host.shadowRoot.append(dialog); dialog.showModal();
    this.visibility = () => { if (doc.hidden) this.close(); };
    doc.addEventListener("visibilitychange", this.visibility);
    this.rotation = new LiveRotation(get("stage"), [get("media")], get("rotate"));
    get("speaker").onclick = async () => {
      const video = findLiveVideo(get("media")); if (!video) return;
      setPlayerMuted(get("media"), !video.muted);
      try { await video.play(); } catch { video.muted = true; }
      const text = copy({ hass }, video.muted ? "Attiva audio" : "Disattiva audio");
      get("speaker").title = text; get("speaker").setAttribute("aria-label", text);
      get("speaker").querySelector("ha-icon").setAttribute("icon", video.muted ? "mdi:volume-off" : "mdi:volume-high");
    };
    try {
      const helpers = await loadHaCardHelpers(this.host);
      if (this.generation !== generation) return;
      const card = await helpers.createCardElement({ type: "picture-entity", entity: entityId,
        camera_view: "live", show_name: false, show_state: false,
        tap_action: { action: "none" }, hold_action: { action: "none" } });
      if (this.generation !== generation) return;
      card.hass = hass; get("media").append(card);
      let initialized;
      this.timer = setInterval(() => {
        const video = findLiveVideo(get("media"));
        get("loading").hidden = Boolean(video && video.readyState >= 2);
        if (video && video !== initialized) {
          initialized = video; setPlayerMuted(get("media"), false);
          video.play().catch(() => {
            if (this.generation === generation) {
              setPlayerMuted(get("media"), true);
              get("status").textContent = copy({ hass }, "Il browser ha bloccato l’audio automatico. Premi Attiva audio per ascoltare.");
            }
          });
        }
        if (video) {
          const text = copy({ hass }, video.muted ? "Attiva audio" : "Disattiva audio");
          get("speaker").title = text; get("speaker").setAttribute("aria-label", text);
          get("speaker").querySelector("ha-icon").setAttribute("icon", video.muted ? "mdi:volume-off" : "mdi:volume-high");
        }
      }, 250);
    } catch {
      if (this.generation !== generation) return;
      get("loading").hidden = true;
      get("status").textContent = copy({ hass }, "Player Home Assistant non disponibile");
    }
  }
  close() {
    ++this.generation; clearInterval(this.timer); this.timer = null;
    if (this.visibility) this.host.ownerDocument.removeEventListener("visibilitychange", this.visibility);
    this.rotation?.dispose(); this.rotation = null;
    this.dialog?.close(); this.dialog?.remove(); this.dialog = null;
  }
}
