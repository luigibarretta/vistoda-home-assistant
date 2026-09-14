import { copy } from "./panel-copy.js";

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
    this.labels = ["USB Blink", "Locale HA", "Backup NFS"];
    for (const [index, key] of this.keys.entries()) {
      const tab = document.createElement("button"); tab.id = `tab-${key}`;
      tab.type = "button"; tab.setAttribute("role", "tab");
      tab.setAttribute("aria-controls", `panel-${key}`);
      tab.addEventListener("click", () => this.select(index));
      tab.addEventListener("keydown", (event) => {
        const target = event.key === "Home" ? 0 : event.key === "End" ? 2
          : event.key === "ArrowRight" ? (index + 1) % 3
            : event.key === "ArrowLeft" ? (index + 2) % 3 : null;
        if (target === null) return;
        event.preventDefault(); this.select(target);
        this.shadowRoot.getElementById(`tab-${this.keys[target]}`).focus();
      });
      this.shadowRoot.querySelector("nav").append(tab);
      const panel = document.createElement("section"); panel.id = `panel-${key}`;
      panel.setAttribute("role", "tabpanel"); panel.setAttribute("aria-labelledby", tab.id);
      const slot = document.createElement("slot"); slot.name = key; panel.append(slot);
      this.shadowRoot.append(panel);
    }
    this.select(0);
  }
  set hass(value) { this._hass = value; this.render(); }
  select(index) {
    this.index = index;
    this.keys.forEach((key, current) => {
      const selected = current === index;
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
      this.shadowRoot.getElementById(`tab-${key}`).textContent = copy(this, this.labels[index]);
    });
  }
}
if (!customElements.get("vistoda-archive-tabs")) customElements.define("vistoda-archive-tabs", ArchiveTabs);
