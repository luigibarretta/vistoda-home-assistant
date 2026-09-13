export const PAGE_SIZES = Object.freeze([10, 25, 50, 100]);

class VistodaPageSize extends (globalThis.HTMLElement || class {}) {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._value = 10; this._disabled = false;
    this.shadowRoot.innerHTML = `<style>
      :host { display:flex; align-items:center; gap:9px; margin:12px 0; min-width:0; }
      span { color:var(--secondary-text-color); font-size:12px; font-weight:650; }
      select { min-width:96px; min-height:44px; box-sizing:border-box; padding:8px 36px 8px 12px;
        border:1px solid var(--divider-color); border-radius:12px; color:var(--primary-text-color);
        background:var(--secondary-background-color); font:inherit; font-weight:700; color-scheme:dark; }
      select:focus-visible { outline:3px solid var(--primary-color,#6246ea); outline-offset:2px; }
      select:disabled { opacity:.45; cursor:not-allowed; }
    </style><label for="picker"><span id="label">Clip per pagina</span></label><select id="picker"></select>`;
    const picker = this.shadowRoot.getElementById("picker");
    for (const size of PAGE_SIZES) {
      const option = document.createElement("option"); option.value = String(size); option.textContent = String(size);
      picker.append(option);
    }
    picker.addEventListener("change", () => {
      this.value = Number(picker.value); this.dispatchEvent(new Event("change", { bubbles: true }));
    });
    this._render();
  }
  get value() { return this._value; }
  set value(value) {
    const numeric = Number(value);
    if (PAGE_SIZES.includes(numeric)) { this._value = numeric; this._render(); }
  }
  get disabled() { return this._disabled; }
  set disabled(value) { this._disabled = Boolean(value); this._render(); }
  localize(language) {
    this.shadowRoot.getElementById("label").textContent = String(language || "").startsWith("it")
      ? "Clip per pagina" : "Clips per page";
  }
  _render() {
    if (!this.shadowRoot) return;
    const picker = this.shadowRoot.getElementById("picker");
    picker.value = String(this._value); picker.disabled = this._disabled;
  }
}

if (globalThis.customElements && !customElements.get("vistoda-page-size")) {
  customElements.define("vistoda-page-size", VistodaPageSize);
}
export const PAGE_SIZE_TEMPLATE = `<vistoda-page-size id="page-size"></vistoda-page-size>`;

export function bindPageSize(root, changed) {
  root.getElementById("page-size").addEventListener("change", (event) => {
    const size = Number(event.currentTarget.value);
    if (!event.currentTarget.disabled && PAGE_SIZES.includes(size)) changed(size);
  });
}
export function renderPageSize(root, size, busy, language = "") {
  const picker = root.getElementById("page-size");
  picker.value = size; picker.disabled = Boolean(busy); picker.localize(language);
}
