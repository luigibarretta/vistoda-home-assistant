// Keep the current player mounted: entering fullscreen must not restart a stream.
export function findLiveVideo(root) {
  if (root?.hidden) return null;
  if (root?.localName === "video") return root;
  for (const child of root?.children || []) {
    const video = findLiveVideo(child.shadowRoot) || findLiveVideo(child);
    if (video) return video;
  }
  return null;
}

export class LiveFullscreen {
  constructor(stage, changed) {
    this.stage = stage;
    this.changed = changed;
    this.document = stage.ownerDocument;
    this.update = () => changed(this.active);
    this.document.addEventListener("fullscreenchange", this.update);
    this.document.addEventListener("webkitfullscreenchange", this.update);
  }

  get active() {
    const root = this.stage.getRootNode();
    return root.fullscreenElement === this.stage ||
      this.document.fullscreenElement === this.stage ||
      this.document.webkitFullscreenElement === this.stage;
  }

  async toggle() {
    if (this.active) return this.exit();
    const currentVideo = findLiveVideo(this.stage);
    const ratio = currentVideo?.videoWidth / currentVideo?.videoHeight;
    this.stage.style?.setProperty("--live-aspect", String(Number.isFinite(ratio) && ratio > 0 ? ratio : 16 / 9));
    // Invoke synchronously from the user's click to retain browser activation.
    if (this.stage.requestFullscreen) await this.stage.requestFullscreen();
    else if (this.stage.webkitRequestFullscreen) await this.stage.webkitRequestFullscreen();
    else {
      const video = findLiveVideo(this.stage);
      if (!video?.webkitEnterFullscreen) throw new Error("fullscreen_unavailable");
      video.webkitEnterFullscreen();
    }
    this.update();
  }

  async exit() {
    if (this.active) {
      if (this.document.exitFullscreen) await this.document.exitFullscreen();
      else await this.document.webkitExitFullscreen?.();
    }
    const video = findLiveVideo(this.stage);
    if (video?.webkitDisplayingFullscreen) video.webkitExitFullscreen?.();
  }

  dispose() {
    this.exit().catch(() => {});
    this.document.removeEventListener("fullscreenchange", this.update);
    this.document.removeEventListener("webkitfullscreenchange", this.update);
  }
}
