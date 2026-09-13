// Rotate the media, not the controls, without replacing the active player.
export class LiveRotation {
  constructor(stage, targets, button) {
    this.stage = stage; this.targets = targets; this.button = button;
    this.active = false;
    this.resize = new ResizeObserver(() => this.update());
    this.resize.observe(stage);
    this.toggle = () => { this.active = !this.active; this.update(); };
    button.addEventListener("click", this.toggle);
  }
  update() {
    const { width, height } = this.stage.getBoundingClientRect();
    for (const target of this.targets) {
      if (this.active) {
        target.style.width = `${height}px`; target.style.height = `${width}px`;
        target.style.inset = "auto"; target.style.left = "50%"; target.style.top = "50%";
        target.style.transform = "translate(-50%, -50%) rotate(90deg)";
      } else {
        for (const key of ["width", "height", "inset", "left", "top", "transform"]) target.style.removeProperty(key);
      }
    }
    this.button.setAttribute("aria-pressed", String(this.active));
  }
  reset() { this.active = false; this.update(); }
  dispose() { this.reset(); this.resize.disconnect(); this.button.removeEventListener("click", this.toggle); }
}
