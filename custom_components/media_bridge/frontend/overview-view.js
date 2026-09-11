import { localizeCopy } from "./panel-copy.js";
import { BASE_STYLES } from "./panel-styles.js";
import { PROVIDERS, PROVIDER_META, providerPath } from "./panel-helpers.js";
import { localize, localizeElements } from "./panel-localize.js";

class VistodaOverview extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._mounted = false;
    this._info = null;
  }

  set hass(value) { this._hass = value; if (this._mounted) this._render(); }
  set info(value) { this._info = value; this._render(); }

  _mount() {
    this._mounted = true;
    this.shadowRoot.innerHTML = `
      <style>${BASE_STYLES}
        .intro { margin-bottom:20px; }
        .intro h2 { margin:0 0 7px; font-size:25px; }
        .grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:16px; }
        article { padding:20px; display:flex; min-height:230px; flex-direction:column; }
        .icon { display:grid; place-items:center; width:48px; height:48px; border-radius:15px;
          color:#fff; background:linear-gradient(145deg,#6246ea,#27b3a2); margin-bottom:15px; }
        .icon ha-icon { --mdc-icon-size:26px; }
        h3 { margin:0 0 6px; font-size:20px; }
        .status { display:flex; justify-content:space-between; align-items:center;
          gap:12px; margin:16px 0; padding-top:14px; border-top:1px solid var(--divider-color); }
        .button { margin-top:auto; display:grid; place-items:center; }
        @media (max-width:850px) { .grid { grid-template-columns:1fr; } article { min-height:0; } }
      </style>
      <section class="intro"><h2 data-i18n="introTitle">Tutti i dispositivi, una sola vista</h2>
        <div class="muted" data-i18n="introBody">Scegli un marchio per vedere le telecamere, rispondere al citofono
        e consultare le registrazioni.</div></section>
      <section class="grid" id="providers" aria-live="polite"></section>`; localizeCopy(this.shadowRoot, this);
  }

  _render() {
    if (!this._mounted) this._mount();
    localizeElements(this.shadowRoot, this._hass);
    const container = this.shadowRoot.getElementById("providers");
    container.replaceChildren(...PROVIDERS.map((provider) => this._providerCard(provider)));
  }

  _providerCard(provider) {
    const meta = PROVIDER_META[provider];
    const state = this._info?.providers?.[provider];
    const configured = Boolean(state?.configured);
    const available = Boolean(state?.available);
    const cameras = state?.counts?.camera || 0;
    const devices = state?.devices?.length || 0;
    const article = document.createElement("article");
    article.className = "card";
    article.innerHTML = `<div class="icon"><ha-icon></ha-icon></div><h3></h3>
      <div class="muted description"></div><div class="status"><span class="summary"></span>
      <span class="badge"></span></div><a class="button primary"></a>`; localizeCopy(article, this);
    article.querySelector("ha-icon").setAttribute("icon", meta.icon);
    article.querySelector("h3").textContent = `Vistoda · ${meta.label}`;
    article.querySelector(".description").textContent = localize(this._hass, `${provider}Description`);
    article.querySelector(".summary").textContent = configured
      ? localize(this._hass, "deviceCount", { devices, cameras }) : localize(this._hass, "notConfigured");
    const badge = article.querySelector(".badge");
    badge.textContent = localize(this._hass, available ? "ready" : configured ? "unavailable" : "absent");
    badge.classList.toggle("off", !available);
    const link = article.querySelector("a");
    link.href = configured ? providerPath(provider) : "/config/integrations/dashboard";
    link.textContent = localize(this._hass, configured ? "openProvider" : "configureProvider", { provider: meta.label });
    link.setAttribute("aria-label", link.textContent);
    return article;
  }
}

if (!customElements.get("vistoda-overview")) {
  customElements.define("vistoda-overview", VistodaOverview);
}
