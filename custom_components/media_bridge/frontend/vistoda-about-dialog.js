import { localizeElements, panelLanguage } from "./panel-localize.js";
import { BASE_STYLES } from "./panel-styles.js";

const GITHUB_PROFILE = "https://github.com/luigibarretta";
const KOFI_PROFILE = "https://ko-fi.com/luigibarretta";
const REPOSITORY = "https://github.com/luigibarretta/vistoda-home-assistant/blob/main";

class VistodaAboutDialog extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._mounted = false;
    this._returnFocus = null;
  }

  set hass(value) {
    this._hass = value;
    this._mount();
    localizeElements(this.shadowRoot, value);
    this._setDocumentLinks();
  }

  connectedCallback() {
    this._mount();
  }

  open(trigger) {
    this._returnFocus = trigger || null;
    this._mount();
    localizeElements(this.shadowRoot, this._hass);
    this._setDocumentLinks();
    const dialog = this.shadowRoot.getElementById("dialog");
    if (!dialog.open) dialog.showModal();
    this.shadowRoot.getElementById("close").focus();
  }

  _mount() {
    if (this._mounted) return;
    this._mounted = true;
    this.shadowRoot.innerHTML = `
      <style>${BASE_STYLES}
        dialog { width:min(620px,calc(100vw - 24px)); max-height:calc(100dvh - 24px);
          overflow:auto; padding:0; color:var(--primary-text-color); border:1px solid var(--divider-color);
          border-radius:22px; background:var(--card-background-color); box-shadow:0 24px 70px #000a; }
        dialog::backdrop { background:#000a; }
        .body { padding:24px; }
        .title-row { display:flex; align-items:flex-start; justify-content:space-between; gap:18px; }
        h2 { margin:4px 0 0; font-size:25px; line-height:1.2; }
        p { line-height:1.5; }
        #close { flex:0 0 44px; padding:8px; }
        .creator { display:grid; grid-template-columns:auto minmax(0,1fr); align-items:center;
          gap:13px; margin:20px 0; padding:15px; border-radius:15px;
          background:var(--secondary-background-color); }
        .creator > ha-icon { --mdc-icon-size:28px; color:var(--primary-color); }
        .creator strong, .creator span { display:block; }
        .creator span { margin-top:3px; color:var(--secondary-text-color); }
        .links { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px; }
        .links a { text-align:center; }
        .notice { margin-top:20px; padding:16px; border:1px solid var(--divider-color);
          border-radius:15px; background:color-mix(in srgb,var(--primary-color) 9%,transparent); }
        .notice h3 { display:flex; align-items:center; gap:8px; margin:0 0 8px; font-size:17px; }
        .notice h3 ha-icon { --mdc-icon-size:22px; }
        .notice p { margin:0; }
        .resources { display:flex; flex-wrap:wrap; gap:8px 18px; margin-top:15px; }
        .resources a { min-height:44px; display:inline-flex; align-items:center; color:var(--primary-text-color); }
        .dialog-actions { display:flex; justify-content:flex-end; margin-top:20px; }
        @media (max-width:520px) {
          .body { padding:18px; }
          .links { grid-template-columns:1fr; }
          .links a { width:100%; }
          .resources { display:grid; grid-template-columns:1fr; gap:0; }
        }
      </style>
      <dialog id="dialog" aria-labelledby="about-title" aria-describedby="about-summary">
        <div class="body">
          <div class="title-row"><div><span class="eyebrow" data-i18n="aboutEyebrow"></span>
            <h2 id="about-title" data-i18n="aboutTitle"></h2></div>
            <button id="close" data-i18n-aria-label="close" data-i18n-title="close">
              <ha-icon icon="mdi:close" aria-hidden="true"></ha-icon></button></div>
          <p class="muted" id="about-summary" data-i18n="aboutSummary"></p>
          <div class="creator"><ha-icon icon="mdi:account-heart-outline" aria-hidden="true"></ha-icon>
            <div><strong>Luigi Barretta</strong><span data-i18n="maintainedBy"></span></div></div>
          <div class="links">
            <a class="button" href="${GITHUB_PROFILE}" target="_blank" rel="noopener noreferrer"
              data-i18n-aria-label="githubProfileNewWindow"><ha-icon icon="mdi:github" aria-hidden="true"></ha-icon>
              <span data-i18n="githubProfile"></span></a>
            <a class="button primary" href="${KOFI_PROFILE}" target="_blank" rel="noopener noreferrer"
              data-i18n-aria-label="supportKofiNewWindow"><ha-icon icon="mdi:coffee-outline" aria-hidden="true"></ha-icon>
              <span data-i18n="supportKofi"></span></a>
          </div>
          <section class="notice" aria-labelledby="independence-title">
            <h3 id="independence-title"><ha-icon icon="mdi:shield-alert-outline" aria-hidden="true"></ha-icon>
              <span data-i18n="independenceTitle"></span></h3>
            <p data-i18n="independenceShort"></p>
          </section>
          <div class="resources">
            <a id="accessibility-link" href="${REPOSITORY}/ACCESSIBILITY.md" target="_blank" rel="noopener noreferrer"
              data-i18n-aria-label="accessibilityPageNewWindow" data-i18n="accessibilityPage"></a>
            <a id="disclaimer-link" href="${REPOSITORY}/DISCLAIMER.md" target="_blank" rel="noopener noreferrer"
              data-i18n-aria-label="fullDisclaimerNewWindow" data-i18n="fullDisclaimer"></a>
          </div>
          <div class="dialog-actions"><button id="done" data-i18n="close"></button></div>
        </div>
      </dialog>`;
    const dialog = this.shadowRoot.getElementById("dialog");
    this.shadowRoot.getElementById("close").addEventListener("click", () => dialog.close());
    this.shadowRoot.getElementById("done").addEventListener("click", () => dialog.close());
    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) dialog.close();
    });
    dialog.addEventListener("close", () => {
      this._returnFocus?.focus();
      this._returnFocus = null;
    });
  }

  _setDocumentLinks() {
    const suffix = panelLanguage(this._hass) === "it" ? ".it" : "";
    this.shadowRoot.getElementById("accessibility-link").href = `${REPOSITORY}/ACCESSIBILITY${suffix}.md`;
    this.shadowRoot.getElementById("disclaimer-link").href = `${REPOSITORY}/DISCLAIMER${suffix}.md`;
  }
}

if (!customElements.get("vistoda-about-dialog")) {
  customElements.define("vistoda-about-dialog", VistodaAboutDialog);
}
