import { copy } from "./panel-copy.js";
import { findLiveVideo } from "./live-fullscreen.js";
import { LiveRotation } from "./live-rotation.js";

// A viewer owns its overlay and timers, never another viewer's shared publisher.
export class BlinkLiveControls {
  constructor(view) {
    this.view = view; this.held = false; this.deadline = Infinity;
    this.rotation = new LiveRotation(view.$("stage"),
      [view.$("live-video"), view.$("legacy-live")], view.$("rotate"));
    const button = view.$("microphone");
    const release = () => {
      if (!this.held) return;
      this.held = false; this.extend();
      view._liveSession?.setMicrophone(false);
    };
    this.release = release;
    window.addEventListener("blur", release);
    window.addEventListener("pagehide", release);
    button.addEventListener("pointerdown", (event) => {
      if (event.button !== 0 || event.isPrimary === false || button.disabled) return;
      event.preventDefault(); button.setPointerCapture(event.pointerId); this.hold();
    });
    for (const type of ["pointerup", "pointercancel", "lostpointercapture", "blur"]) button.addEventListener(type, release);
    button.addEventListener("keydown", (event) => {
      if (![" ", "Enter"].includes(event.key)) return;
      event.preventDefault(); if (!event.repeat) this.hold();
    });
    button.addEventListener("keyup", (event) => {
      if ([" ", "Enter"].includes(event.key)) { event.preventDefault(); release(); }
    });
    button.addEventListener("contextmenu", (event) => event.preventDefault());
    view.$("continue").addEventListener("click", () => this.extend());
    const dialog = view.$("mobile-live-dialog");
    dialog.addEventListener("cancel", (event) => { event.preventDefault(); this.close(); });
    dialog.addEventListener("close", () => { if (this.mobile) this.close(); });
    this.visibility = () => { if (document.hidden) this.close(); };
    document.addEventListener("visibilitychange", this.visibility);
    this.leave = () => {
      if (!["/vistoda/blink", "/vistoda-blink"].includes(location.pathname.replace(/\/$/, ""))) this.close();
    };
    this.pagehide = () => this.close();
    window.addEventListener("location-changed", this.leave);
    window.addEventListener("popstate", this.leave);
    window.addEventListener("pagehide", this.pagehide);
  }
  hold() {
    if (this.held) return;
    this.held = true;
    this.view._liveSession?.setMicrophone(true);
  }
  open() {
    this.loading = setInterval(() => {
      const video = findLiveVideo(this.view.$("stage"));
      this.view.$("live-loader").hidden = Boolean(video && video.readyState >= 2);
    }, 250);
    this.view.$("live-loader").hidden = false;
    this.started = performance.now(); this.deadline = Infinity; this.interval = 30000; this.warning = 10000;
    this.extend();
    this.mobile = matchMedia("(max-width: 767px)").matches ||
      matchMedia("(pointer: coarse) and (max-height: 767px)").matches;
    if (!this.mobile) return;
    this.placeholder = document.createComment("Blink stage");
    const stage = this.view.$("stage"); stage.before(this.placeholder);
    this.view.$("mobile-stage-slot").append(stage);
    this.view.$("mobile-live-dialog").showModal();
  }
  update(state) {
    if (state.phase !== "active") return;
    const timing = state.sessionTiming;
    if (timing && Number.isFinite(timing.remaining_ms)) {
      this.deadline = Math.min(this.deadline, performance.now() + Math.max(0, timing.remaining_ms));
      if (Number.isFinite(timing.continue_interval) && timing.continue_interval > 0) this.interval = timing.continue_interval * 1000;
      if (Number.isFinite(timing.continue_warning) && timing.continue_warning >= 0) this.warning = Math.min(this.interval, timing.continue_warning * 1000);
    }
    if (!this.timer) {
      this.extend();
      this.timer = setInterval(() => this.tick(), 250);
    }
  }
  extend() { this.promptDeadline = performance.now() + (this.interval || 30000); this.view.$("continue").hidden = true; }
  tick() {
    const now = performance.now();
    const total = now >= this.deadline;
    if (total || (!this.held && now >= this.promptDeadline)) {
      this.close();
      this.view._liveState.message = copy(this.view, total
        ? "Durata massima del live raggiunta. Riaprilo per continuare."
        : "Live terminato per inattività. Riaprilo per continuare.");
      this.view._renderLive(); return;
    }
    this.view.$("continue").hidden = this.held || now < this.promptDeadline - this.warning;
  }
  close() {
    this.view._stopLiveForCameraChange();
    this.view._renderLive(); this.view._showImage(Boolean(this.view.$("snapshot").src));
  }
  reset() {
    this.view._recordingMenu?.close();
    this.rotation.reset();
    clearInterval(this.loading); this.loading = null;
    this.view.$("live-loader").hidden = true;
    this.held = false; clearInterval(this.timer); this.timer = null;
    this.view.$("continue").hidden = true;
    if (this.mobile) {
      this.mobile = false;
      this.placeholder?.replaceWith(this.view.$("stage")); this.placeholder = null;
      this.view.$("mobile-live-dialog").close();
      this.view.$("live").focus();
    }
  }
  dispose() {
    this.rotation.dispose();
    this.release(); this.reset(); document.removeEventListener("visibilitychange", this.visibility);
    window.removeEventListener("blur", this.release); window.removeEventListener("pagehide", this.release);
    window.removeEventListener("location-changed", this.leave);
    window.removeEventListener("popstate", this.leave);
    window.removeEventListener("pagehide", this.pagehide);
  }
}
