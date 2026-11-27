import { copy } from "./panel-copy.js";
import { tabEnabled, visibleTab } from "./archive-features-model.js";

// Keep panels mounted: changing tabs must not reset paging, filters or selection.
class ArchiveTabs extends HTMLElement {
  constructor() {
    super(); this.attachShadow({ mode: "open" });
    this.shadowRoot.innerHTML = `<style>
      :host { display:block; min-width:0; } [hidden] { display:none !important; }
      nav { display:flex; gap:4px; border-bottom:1px solid var(--divider-color); margin-bottom:16px; }
      button { flex:1; min-width:0; min-height:48px; padding:8px; border:0;
        border-bottom:3px solid transparent; background:none; color:var(--primary-text-color); font:inherit; }
      button[aria-selected="true"] { border-color:var(--primary-color); font-weight:700; }
      button:focus-visible { outline:3px solid var(--primary-color); outline-offset:-3px; }
      @media (max-width:600px) { button { font-size:14px; padding:8px 4px; line-height:1.3; } }
    </style><nav role="tablist"></nav>`;
    this.keys = ["usb", "local", "network"];
    this._features = null;
    this.labels = ["USB Blink", "Locale HA", "Backup NFS"];
    for (const [index, key] of this.keys.entries()) {
      const tab = document.createElement("button"); tab.id = `tab-${key}`;
      tab.type = "button"; tab.setAttribute("role", "tab");
      tab.setAttribute("aria-controls", `panel-${key}`);
      tab.addEventListener("click", () => this.select(index));
      tab.addEventListener("keydown", (event) => {
        const active = this._active(), place = active.indexOf(index);
        const target = event.key === "Home" ? active[0] : event.key === "End" ? active.at(-1)
          : event.key === "ArrowRight" ? active[(place + 1) % active.length]
            : event.key === "ArrowLeft" ? active[(place + active.length - 1) % active.length] : null;
        if (target === null || target === undefined) return;
        event.preventDefault(); this.select(target);
        this.shadowRoot.getElementById(`tab-${this.keys[target]}`).focus();
      });
      this.shadowRoot.querySelector("nav").append(tab);
      const panel = document.createElement("section"); panel.id = `panel-${key}`;
      panel.setAttribute("role", "tabpanel"); panel.setAttribute("aria-labelledby", tab.id);
      const slot = document.createElement("slot"); slot.name = key; panel.append(slot);
      this.shadowRoot.append(panel);
    }
    const none = document.createElement("p"); none.id = "none"; none.hidden = true;
    none.style.cssText = "color:var(--secondary-text-color);margin:8px 0";
    this.shadowRoot.append(none);
    this.select(0);
  }
  set hass(value) { this._hass = value; this.render(); }
  /** Archives the user turned off disappear; the tab on show moves to one that is still active. */
  set features(value) {
    this._features = value; this.render();
    const keep = visibleTab(value, this.keys, this.keys[this.index]);
    if (keep !== null && keep !== this.keys[this.index]) this.select(this.keys.indexOf(keep));
  }
  _active() {
    return this.keys.map((key, index) => (tabEnabled(this._features, key) ? index : -1)).filter((i) => i >= 0);
  }
  select(index) {
    this.index = index;
    this.keys.forEach((key, current) => {
      const selected = current === index && tabEnabled(this._features, key);
      const tab = this.shadowRoot.getElementById(`tab-${key}`);
      tab.setAttribute("aria-selected", String(selected)); tab.tabIndex = selected ? 0 : -1;
      this.shadowRoot.getElementById(`panel-${key}`).hidden = !selected;
      if (!selected) this.querySelector(`[slot="${key}"]`)?.pausePlayback?.();
    });
    this.render();
    this.dispatchEvent(new CustomEvent("archive-tab-change", { detail: this.keys[index] }));
  }
  render() {
    this.keys.forEach((key, index) => {
      const tab = this.shadowRoot.getElementById(`tab-${key}`), on = tabEnabled(this._features, key);
      tab.textContent = copy(this, this.labels[index]); tab.hidden = !on;
      if (!on) this.shadowRoot.getElementById(`panel-${key}`).hidden = true;
    });
    const none = this.shadowRoot.getElementById("none"), any = this._active().length > 0;
    none.hidden = any; none.textContent = any ? "" : copy(this, "Nessun archivio attivo. Attivane uno qui sopra.");
  }
}
if (!customElements.get("vistoda-archive-tabs")) customElements.define("vistoda-archive-tabs", ArchiveTabs);
