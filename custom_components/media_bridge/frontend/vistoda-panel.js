import { localizeCopy } from "./panel-copy.js";
import "./overview-view.js";
import "./ring-view.js";
import "./blink-view.js";
import "./ezviz-view.js";
import "./vistoda-about-dialog.js";
import { BASE_STYLES } from "./panel-styles.js";
import { localize, localizeElements } from "./panel-localize.js";
import {
  homeAssistantPath,
  isVistodaPath,
  PROVIDERS,
  PROVIDER_META,
  canonicalVistodaPath,
  providerFromPanel,
  providerPath,
} from "./panel-helpers.js";

const VIEW_TAGS = {
  overview: "vistoda-overview",
  ring: "vistoda-ring-view",
  blink: "vistoda-blink-view",
  ezviz: "vistoda-ezviz-view",
};

class VistodaPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._mounted = false;
    this._provider = "overview";
    this._info = null;
    this._child = null;
  }

  set hass(value) {
    this._hass = value;
    this._ensureMounted();
    if (this._child) this._child.hass = value;
    if (this._mounted) this._localize();
  }

  set panel(value) {
    this._panel = value;
    this._syncProvider();
  }

  set route(value) {
    this._route = value;
    this._syncProvider();
  }

  _syncProvider() {
    const provider = providerFromPanel(this._panel);
    if (this._mounted && provider !== this._provider) {
      this._mounted = false;
      this.shadowRoot.replaceChildren();
    }
    this._provider = provider;
    this._ensureMounted();
    this._canonicalizeLegacyRoute();
  }

  _canonicalizeLegacyRoute() {
    const pathname = globalThis.location?.pathname || "";
    const canonical = canonicalVistodaPath(pathname);
    if (canonical === pathname) return;
    const suffix = `${globalThis.location.search || ""}${globalThis.location.hash || ""}`;
    globalThis.history.replaceState(null, "", `${canonical}${suffix}`);
    globalThis.dispatchEvent(new CustomEvent("location-changed"));
  }

  _ensureMounted() {
    if (this._mounted || !this._hass) return;
    this._mount();
  }

  _mount() {
    this._mounted = true;
    const activeLabel = this._provider === "overview"
      ? "Centro di controllo privato" : PROVIDER_META[this._provider].description;
    this.shadowRoot.innerHTML = `
      <style>${BASE_STYLES}
        main { width:min(1120px,100%); min-width:0; margin:0 auto; padding:26px 18px 48px; }
        header { display:flex; align-items:center; justify-content:space-between; gap:20px;
          margin-bottom:20px; }
        .header-start { display:flex; align-items:center; gap:12px; min-width:0; flex:1; }
        .identity { display:flex; align-items:center; gap:15px; min-width:0; flex:1; }
        .identity > div:last-child { min-width:0; }
        .mark { display:grid; place-items:center; width:56px; height:56px; border-radius:18px;
          color:#fff; background:linear-gradient(145deg,#6246ea,#27b3a2); }
        .mark ha-icon { --mdc-icon-size:30px; }
        h1 { margin:0; font-size:28px; } header p { margin:4px 0 0; }
        nav { display:flex; min-width:0; max-width:100%; gap:7px; padding:7px; overflow-x:auto; margin-bottom:22px;
          border:1px solid var(--divider-color); border-radius:16px;
          background:var(--card-background-color); }
        nav a { min-height:44px; display:flex; align-items:center; justify-content:center; gap:7px;
          flex:1 0 auto; padding:8px 13px; border-radius:11px; color:var(--secondary-text-color);
          text-decoration:none; font-weight:650; }
        nav a.active { color:#fff; background:linear-gradient(135deg,#6246ea,#4967e9); }
        nav ha-icon { --mdc-icon-size:20px; }
        .header-actions { display:flex; align-items:center; gap:8px; flex:0 0 auto; }
        #back { display:none; } #reload, #about { flex:0 0 auto; }
        @media (max-width:600px) {
          nav { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); }
          nav a { min-width:0; padding:8px; }
          main { padding:18px 12px 36px; } header { align-items:flex-start; gap:8px; }
          #back { display:grid; place-items:center; min-width:44px; padding:8px; }
          .mark { display:none; } .identity { gap:8px; } h1 { font-size:24px; }
          header p { white-space:normal; overflow:visible; line-height:1.35; }
          #reload, #about { min-width:44px; padding:8px; }
          #reload span, #about span { display:none; }
        }
      </style>
      <main><header><div class="header-start"><button id="back"
        aria-label="Torna indietro, fuori da Vistoda" title="Torna alla pagina precedente"
        data-tooltip="Esce da Vistoda e torna alla pagina precedente"><ha-icon icon="mdi:arrow-left"></ha-icon></button>
        <div class="identity"><div class="mark">
        <ha-icon icon="mdi:shield-home"></ha-icon></div><div><h1>Vistoda</h1>
        <p class="muted"></p></div></div></div><div class="header-actions">
        <button id="about" aria-label="Informazioni e supporto" title="Informazioni e supporto">
          <ha-icon icon="mdi:information-outline"></ha-icon><span>Info</span></button>
        <button id="reload" aria-label="Aggiorna inventario" title="Aggiorna inventario Vistoda">
          <ha-icon icon="mdi:refresh"></ha-icon><span><span data-copy="Aggiorna">Aggiorna</span></span></button></div></header>
        <nav aria-label="Provider Vistoda"><a href="/vistoda" data-provider="overview">
          <ha-icon icon="mdi:view-dashboard"></ha-icon>Panoramica</a>
          ${PROVIDERS.map((provider) => `<a href="${providerPath(provider)}" data-provider="${provider}">
            <ha-icon icon="${PROVIDER_META[provider].icon}"></ha-icon>
            ${PROVIDER_META[provider].label}</a>`).join("")}
        </nav><section id="inventory-status" class="card empty" role="status" hidden></section>
        <section id="content" aria-live="polite"></section>
        <vistoda-about-dialog id="about-dialog"></vistoda-about-dialog></main>`; localizeCopy(this.shadowRoot, this);
    this.shadowRoot.querySelector("header p").textContent = activeLabel;
    this.shadowRoot.querySelector("#back").dataset.i18nAriaLabel = "back";
    this.shadowRoot.querySelector("#back").dataset.i18nTitle = "back";
    this.shadowRoot.querySelector("#back").removeAttribute("data-tooltip");
    this.shadowRoot.querySelector("#reload").dataset.i18nAriaLabel = "refreshInventory";
    this.shadowRoot.querySelector("#reload").dataset.i18nTitle = "refreshInventory";
    this.shadowRoot.querySelector("#reload").removeAttribute("data-tooltip");
    this.shadowRoot.querySelector("#reload span").dataset.i18n = "reload";
    this.shadowRoot.querySelector("#about").dataset.i18nAriaLabel = "aboutButton";
    this.shadowRoot.querySelector("#about").dataset.i18nTitle = "aboutButton";
    this.shadowRoot.querySelector("nav").dataset.i18nAriaLabel = "navigation";
    const overview = this.shadowRoot.querySelector('[data-provider="overview"]');
    const label = document.createElement("span"); label.dataset.i18n = "overview";
    overview.lastChild.replaceWith(label);
    this._localize();
    this.shadowRoot.querySelectorAll("nav a").forEach((link) => {
      const active = link.dataset.provider === this._provider;
      link.classList.toggle("active", active);
      if (active) link.setAttribute("aria-current", "page");
      link.addEventListener("click", (event) => {
        event.preventDefault();
        this._navigate(link.getAttribute("href"));
      });
    });
    this.shadowRoot.getElementById("back").addEventListener("click", () => this._leavePanel());
    this.shadowRoot.getElementById("about").addEventListener("click", (event) => {
      this.shadowRoot.getElementById("about-dialog").open(event.currentTarget);
    });
    this.shadowRoot.getElementById("reload").addEventListener("click", () => this._loadInfo());
    this.shadowRoot.getElementById("about-dialog").hass = this._hass;
    this._child = document.createElement(VIEW_TAGS[this._provider]);
    this._child.hass = this._hass;
    this.shadowRoot.getElementById("content").replaceChildren(this._child);
    this._loadInfo();
  }

  _leavePanel() {
    const fallback = () => {
      if (isVistodaPath(globalThis.location?.pathname)) this._navigate(homeAssistantPath(this._hass));
    };
    if (globalThis.history?.length > 1) {
      globalThis.history.back();
      globalThis.setTimeout(fallback, 500);
    } else {
      this._navigate(homeAssistantPath(this._hass));
    }
  }

  _localize() {
    localizeElements(this.shadowRoot, this._hass);
    this.shadowRoot.getElementById("about-dialog").hass = this._hass;
    this.shadowRoot.querySelector("header p").textContent = localize(this._hass,
      this._provider === "overview" ? "controlCenter" : `${this._provider}Description`);
  }

  _navigate(path) {
    globalThis.history.pushState(null, "", path);
    globalThis.dispatchEvent(new CustomEvent("location-changed"));
  }

  async _loadInfo() {
    const button = this.shadowRoot.getElementById("reload");
    const status = this.shadowRoot.getElementById("inventory-status");
    const content = this.shadowRoot.getElementById("content");
    if (button) button.disabled = true;
    status.hidden = false;
    status.textContent = localize(this._hass, "loading");
    content.hidden = !this._info || this._info.error;
    try {
      this._info = await this._hass.callWS({ type: "media_bridge/panel/info" });
      status.hidden = true;
      content.hidden = false;
    } catch (_error) {
      status.textContent = localize(this._hass, "inventoryError");
      content.hidden = true;
      this._info = { error: true };
    } finally {
      if (button) button.disabled = false;
    }
    if (this._child) this._child.info = this._info;
  }
}

if (!customElements.get("vistoda-panel")) {
  customElements.define("vistoda-panel", VistodaPanel);
}
