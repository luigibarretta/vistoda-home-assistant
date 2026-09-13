export const PAGE_SIZES = Object.freeze([10, 25, 50, 100]);

class VistodaPageSize extends (globalThis.HTMLElement || class {}) {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._value = 10; this._disabled = false;
    this.shadowRoot.innerHTML = `<style>
      :host { display:flex; align-items:center; gap:9px; margin:12px 0; min-width:0; }
      span { color:var(--secondary-text-color); font-size:12px; font-weight:650; }
      div { display:inline-flex; padding:3px; border:1px solid var(--divider-color);
        border-radius:12px; background:var(--secondary-background-color); }
      button { min-width:44px; min-height:44px; padding:6px 9px; border:0; border-radius:9px;
        color:var(--secondary-text-color); background:transparent; font:inherit; font-weight:700;
        cursor:pointer; }
      button[aria-pressed="true"] { color:#fff; background:var(--primary-color,#6246ea); }
      button:focus-visible { outline:3px solid var(--primary-color,#6246ea); outline-offset:2px; }
      button:disabled { opacity:.45; cursor:not-allowed; }
      @media(max-width:420px) { :host { align-items:flex-start; flex-direction:column; }
        div { display:grid; grid-template-columns:repeat(2,minmax(44px,1fr)); width:100%; }
        button { min-width:44px; } }
    </style><span id="label">Clip per pagina</span><div role="group" aria-labelledby="label"></div>`;
    const group = this.shadowRoot.querySelector("div");
    for (const size of PAGE_SIZES) {
      const button = document.createElement("button");
      button.type = "button"; button.dataset.size = String(size); button.textContent = String(size);
      button.addEventListener("click", () => {
        if (this.disabled || this.value === size) return;
        this.value = size; this.dispatchEvent(new Event("change", { bubbles: true }));
      });
      button.addEventListener("keydown", (event) => this._key(event, size));
      group.append(button);
    }
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
  _key(event, current) {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    let index = PAGE_SIZES.indexOf(current);
    if (event.key === "Home") index = 0;
    else if (event.key === "End") index = PAGE_SIZES.length - 1;
    else index = (index + (event.key === "ArrowRight" ? 1 : -1) + PAGE_SIZES.length) % PAGE_SIZES.length;
    const next = PAGE_SIZES[index]; this.value = next;
    this.shadowRoot.querySelector(`[data-size="${next}"]`).focus();
    this.dispatchEvent(new Event("change", { bubbles: true }));
  }
  _render() {
    if (!this.shadowRoot) return;
    for (const button of this.shadowRoot.querySelectorAll("button")) {
      const active = Number(button.dataset.size) === this._value;
      button.setAttribute("aria-pressed", String(active));
      button.tabIndex = active ? 0 : -1; button.disabled = this._disabled;
    }
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
