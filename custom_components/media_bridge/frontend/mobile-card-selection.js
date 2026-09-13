const CONTROL = "button,input,a,select,textarea,label";

export class MobileCardSelection {
  constructor(root, selector, options) {
    this.root = root; this.selector = selector; this.options = options;
    this.mode = false; this.pointer = null;
    this.down = (event) => this._down(event);
    this.move = (event) => this._move(event);
    this.up = (event) => this._up(event);
    this.click = (event) => this._click(event);
    root.addEventListener("pointerdown", this.down);
    root.addEventListener("pointermove", this.move, { passive: false });
    for (const type of ["pointerup", "pointercancel"]) root.addEventListener(type, this.up);
    root.addEventListener("click", this.click, true);
  }
  setMode(value) {
    this.mode = Boolean(value); this.root.host?.toggleAttribute("selection-mode", this.mode);
    this.options.render();
  }
  _row(event) {
    return event.composedPath?.().find((node) => node.matches?.(this.selector)) || null;
  }
  _mobile() {
    return globalThis.matchMedia?.("(max-width: 650px), (pointer: coarse)").matches;
  }
  _down(event) {
    const row = this._row(event);
    if (!this._mobile() || event.button > 0 || event.isPrimary === false || !row ||
        event.composedPath().some((node) => node !== row && node.matches?.(CONTROL))) return;
    this.pointer = { id: event.pointerId, row, x: event.clientX, y: event.clientY, armed: false };
    this.timer = globalThis.setTimeout(() => {
      if (!this.pointer) return;
      this.pointer.armed = true; this.setMode(true);
      this.options.select(row.dataset.selectionKey, true);
      try { row.setPointerCapture?.(event.pointerId); } catch { /* synthetic pointers */ }
      globalThis.navigator?.vibrate?.(20);
    }, 420);
  }
  _move(event) {
    const pointer = this.pointer;
    if (!pointer || pointer.id !== event.pointerId) return;
    const distance = Math.hypot(event.clientX - pointer.x, event.clientY - pointer.y);
    if (!pointer.armed && distance > 12) { this._clear(); return; }
    if (!pointer.armed) return;
    event.preventDefault();
    const element = this.root.elementFromPoint?.(event.clientX, event.clientY) ||
      globalThis.document?.elementFromPoint?.(event.clientX, event.clientY);
    const row = element?.closest?.(this.selector);
    if (row?.dataset.selectionKey) this.options.select(row.dataset.selectionKey, true);
  }
  _up(event) {
    if (this.pointer?.id !== event.pointerId) return;
    if (this.pointer.armed) {
      event.preventDefault(); this.ignoreClick = true;
      globalThis.setTimeout(() => { this.ignoreClick = false; }, 0);
    }
    this._clear();
  }
  _click(event) {
    if (this.ignoreClick) {
      this.ignoreClick = false; event.preventDefault(); event.stopPropagation(); return;
    }
    if (!this.mode || event.composedPath().some((node) => node.matches?.(CONTROL))) return;
    const row = this._row(event); if (!row?.dataset.selectionKey) return;
    event.preventDefault(); event.stopPropagation();
    this.options.select(row.dataset.selectionKey, !this.options.selected(row.dataset.selectionKey));
  }
  _clear() { globalThis.clearTimeout(this.timer); this.timer = null; this.pointer = null; }
  dispose() {
    this._clear(); this.root.removeEventListener("pointerdown", this.down);
    this.root.removeEventListener("pointermove", this.move);
    for (const type of ["pointerup", "pointercancel"]) this.root.removeEventListener(type, this.up);
    this.root.removeEventListener("click", this.click, true);
  }
}
