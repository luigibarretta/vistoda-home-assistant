// A timed provider capture closes only this viewer, never the shared publisher.
// Count delivered media time, not loading time or wall-clock time in a stalled player.
export class LiveRecordingDeadline {
  constructor(finished) { this.finished = finished; this.reset(); }
  reset() { this.remaining = null; this.video = null; this.position = null; }
  start(seconds) { this.reset(); this.remaining = seconds > 0 ? seconds : null; }
  update(video, active) {
    if (this.remaining === null) return;
    if (!active || !video || video.paused || video.readyState < 2) {
      this.video = null; this.position = null; return;
    }
    const position = video.currentTime;
    if (video === this.video && this.position !== null && Number.isFinite(position)) {
      // Discontinuities/reconnects are not recorded duration.
      const delta = position - this.position;
      if (delta > 0 && delta <= 1) this.remaining -= delta;
    }
    this.video = video; this.position = position;
    if (this.remaining <= 0) { this.reset(); this.finished(); }
  }
}
