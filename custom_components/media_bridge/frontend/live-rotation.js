// Rotate the media, not the controls, without replacing the active player.
export class LiveRotation {
  constructor(stage, targets, button, translate = (value) => value) {
    this.stage = stage; this.targets = targets; this.button = button;
    this.translate = translate;
    this.modes = ["auto", "off", "rotate"]; this.mode = "auto";
    this.resize = new ResizeObserver(() => this.update());
    this.resize.observe(stage);
    this.toggle = () => {
      this.mode = this.modes[(this.modes.indexOf(this.mode) + 1) % this.modes.length]; this.update();
    };
    this.orientation = () => this.update();
    globalThis.screen?.orientation?.addEventListener?.("change", this.orientation);
    globalThis.addEventListener?.("orientationchange", this.orientation);
    button.addEventListener("click", this.toggle);
  }
  update() {
    const { width, height } = this.stage.getBoundingClientRect();
    const portrait = globalThis.matchMedia?.("(orientation: portrait)").matches;
    const active = this.mode === "rotate" || (this.mode === "auto" && portrait);
    for (const target of this.targets) {
      if (active) {
        target.style.width = `${height}px`; target.style.height = `${width}px`;
        target.style.inset = "auto"; target.style.left = "50%"; target.style.top = "50%";
        target.style.transform = "translate(-50%, -50%) rotate(90deg)";
      } else {
        for (const key of ["width", "height", "inset", "left", "top", "transform"]) target.style.removeProperty(key);
      }
    }
    const labels = { auto: "Rotazione automatica", off: "Rotazione disattivata", rotate: "Rotazione di 90 gradi" };
    const icons = { auto: "mdi:screen-rotation", off: "mdi:screen-rotation-off", rotate: "mdi:phone-rotate-landscape" };
    this.button.setAttribute("aria-pressed", String(this.mode !== "off"));
    this.button.setAttribute("data-rotation", this.mode);
    const label = this.translate(labels[this.mode]);
    this.button.setAttribute("aria-label", label); this.button.title = label;
    this.button.querySelector("ha-icon")?.setAttribute("icon", icons[this.mode]);
  }
  reset() { this.mode = "auto"; this.update(); }
  dispose() {
    this.reset(); this.resize.disconnect(); this.button.removeEventListener("click", this.toggle);
    globalThis.screen?.orientation?.removeEventListener?.("change", this.orientation);
    globalThis.removeEventListener?.("orientationchange", this.orientation);
  }
}
