// Presents SceneTrove to administrators on the EZVIZ details page while the
// entry has no SceneTrove address; each browser can dismiss it for good.
import { localizeCopy } from "./panel-copy.js";

const DISMISSED = "vistoda.scenetrove.card.dismissed";
const TEXT = "SceneTrove archivia le registrazioni delle telecamere e le mostra su una timeline. Se lo usi, "
  + "imposta il suo indirizzo nelle opzioni dell’integrazione Vistoda: ogni evento si aprirà in SceneTrove al suo istante.";

function storage() {
  try { return globalThis.localStorage; } catch { return null; } // private mode
}

class VistodaSceneTroveCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this.shadowRoot.innerHTML = `<style>
      :host{display:block}:host([hidden]){display:none}
      section{margin-top:16px;padding:12px 16px;border:1px solid var(--divider-color);border-radius:12px}
      h3{margin:0 0 6px;font-size:15px}p{margin:0;color:var(--secondary-text-color);font-size:13px}
      button{margin-top:8px;min-height:44px;padding:0 14px;border:0;border-radius:12px;background:transparent;
        color:var(--primary-color);cursor:pointer}button:focus-visible{outline:2px solid var(--primary-color)}
    </style><section><h3>SceneTrove</h3>
      <p data-copy="${TEXT}">${TEXT}</p>
      <button id="dismiss" data-copy="Non mostrare più">Non mostrare più</button></section>`;
    this.shadowRoot.getElementById("dismiss").addEventListener("click", () => {
      storage()?.setItem(DISMISSED, "1");
      this.hidden = true;
    });
  }

  configure(hass, entry) {
    this._hass = hass;
    localizeCopy(this.shadowRoot, this);
    this.hidden = !hass?.user?.is_admin || !entry || Boolean(entry.scenetrove_url)
      || storage()?.getItem(DISMISSED) === "1";
  }
}

if (!customElements.get("vistoda-scenetrove-card")) {
  customElements.define("vistoda-scenetrove-card", VistodaSceneTroveCard);
}
