import { LiveRotation } from "./live-rotation.js";
import { RingAudioSession } from "./ring-audio-session.js";
import { copy } from "./panel-copy.js";

export class RingCameraDialog {
  constructor(host) { this.host = host; }
  open(hass, camera) {
    this.close();
    if (!camera) return;
    const doc = this.host.ownerDocument;
    const dialog = doc.createElement("dialog"); this.dialog = dialog;
    dialog.setAttribute("aria-label", camera.name);
    dialog.style.cssText = "margin:0;padding:0;border:0;width:100vw;max-width:none;height:100dvh;max-height:none;background:#000;color:#fff";
    const container = doc.createElement("div"); container.style.height = "100%"; dialog.append(container);
    const root = container.attachShadow({ mode:"open" });
    root.innerHTML = `<style>
      #stage { position:relative;width:100%;height:100%;overflow:hidden; }
      video { position:absolute;inset:0;width:100%;height:100%;object-fit:contain; }
      nav { position:absolute;z-index:3;top:max(12px,env(safe-area-inset-top));right:12px;display:flex;gap:8px; }
      button { width:44px;height:44px;border:1px solid #999;border-radius:50%;color:#fff;background:#181818;cursor:pointer; }
      button:focus-visible { outline:3px solid #00bcd4;outline-offset:2px; }
      #mic { position:absolute;bottom:max(24px,env(safe-area-inset-bottom));left:calc(50% - 22px); }
      #status { position:absolute;bottom:80px;left:16px;right:16px;text-align:center; }
      #loading { position:absolute;top:calc(50% - 20px);left:calc(50% - 20px);width:40px;height:40px;border:4px solid #555;border-top-color:#fff;border-radius:50%;animation:spin 1s linear infinite; }
      #loading[hidden] { display:none; } @keyframes spin { to { transform:rotate(360deg); } }
      @media(prefers-reduced-motion:reduce) { #loading { animation:none; } }
    </style><div id="stage"><video autoplay playsinline></video><div id="loading" aria-hidden="true"></div>
      <nav><button id="speaker"><ha-icon></ha-icon></button><button id="rotate" aria-pressed="false"><ha-icon icon="mdi:screen-rotation"></ha-icon></button>
      <button id="close"><ha-icon icon="mdi:close"></ha-icon></button></nav>
      <p id="status" role="status"></p><button id="mic" disabled aria-pressed="false"><ha-icon icon="mdi:microphone-off"></ha-icon></button></div>`;
    const get = id => root.getElementById(id), video = root.querySelector("video");
    const label = (id, text) => { get(id).title = copy({ hass }, text); get(id).setAttribute("aria-label", copy({ hass }, text)); };
    label("rotate", "Ruota visualizzazione"); label("close", "Chiudi live"); label("mic", "Attiva microfono");
    const speaker = () => {
      label("speaker", video.muted ? "Attiva audio" : "Disattiva audio");
      get("speaker").querySelector("ha-icon").setAttribute("icon", video.muted ? "mdi:volume-off" : "mdi:volume-high");
    };
    speaker(); get("speaker").onclick = async () => { video.muted = !video.muted; try { await video.play(); } catch { video.muted = true; } speaker(); };
    get("close").onclick = () => this.close();
    dialog.addEventListener("cancel", event => { event.preventDefault(); this.close(); });
    this.host.shadowRoot.append(dialog); dialog.showModal();
    this.rotation = new LiveRotation(get("stage"), [video], get("rotate"),
      (label) => copy(this.host, label));
    this.visibility = () => { if (doc.hidden) this.close(); };
    doc.addEventListener("visibilitychange", this.visibility);
    const session = new RingAudioSession(hass, { entry_id:camera.entry_id, camera_id:camera.device_id }, video, state => {
      if (this.session !== session) return;
      get("status").textContent = state.message || copy({ hass }, state.phase === "active" ? "Ascolto attivo" : "Connessione…");
      get("mic").disabled = state.phase !== "active";
      get("mic").setAttribute("aria-pressed", String(state.mode === "talk"));
      label("mic", state.mode === "talk" ? "Disattiva microfono" : "Attiva microfono");
      get("mic").querySelector("ha-icon").setAttribute("icon", state.mode === "talk" ? "mdi:microphone" : "mdi:microphone-off");
      if (["error", "idle", "cooldown"].includes(state.phase)) get("loading").hidden = true;
    });
    this.session = session;
    video.onplaying = () => { get("loading").hidden = true; speaker(); };
    get("mic").onclick = () => session.switchMode(session.mode === "talk" ? "listen" : "talk");
    session.start("listen");
  }
  close() {
    const session = this.session; this.session = null; session?.destroy();
    if (this.visibility) this.host.ownerDocument.removeEventListener("visibilitychange", this.visibility);
    this.rotation?.dispose(); this.rotation = null;
    this.dialog?.close(); this.dialog?.remove(); this.dialog = null;
  }
}
