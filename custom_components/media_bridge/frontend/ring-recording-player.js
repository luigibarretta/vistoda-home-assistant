export class RingRecordingPlayer {
  constructor(host) {
    this.host = host;
    this.activeId = null;
    this.loadingId = null;
    this.mediaUrl = null;
    this.player = null;
    this.request = 0;
  }

  isOpen(recordingId) {
    return [this.activeId, this.loadingId].includes(recordingId);
  }

  async play(recording) {
    this.release();
    const request = this.request;
    this.loadingId = recording.recording_id;
    this.host.render();
    try {
      const result = await this.host.hass.callWS({
        type: "media_bridge/ring/recordings/read",
        entry_id: this.host.entry.entry_id,
        recording_id: recording.recording_id,
      });
      if (request !== this.request) return;
      const binary = atob(result.media_base64);
      const bytes = Uint8Array.from(binary, (character) => character.charCodeAt(0));
      this.mediaUrl = URL.createObjectURL(new Blob([bytes], { type: result.media_type }));
      this.activeId = recording.recording_id;
      this.host.status("");
    } catch (_error) {
      if (request === this.request) this.host.status("Riproduzione non disponibile.");
    } finally {
      if (request !== this.request) return;
      this.loadingId = null;
      this.host.render();
      this.player?.play().catch(() => {});
    }
  }

  detail(recording) {
    const wrap = document.createElement("div");
    if (this.loadingId === recording.recording_id) {
      wrap.className = "player hint";
      wrap.innerHTML = '<ha-icon icon="mdi:loading"></ha-icon> Caricamento audio…';
      wrap.append(this._closeButton());
      return wrap;
    }
    const player = document.createElement("div");
    player.className = "player";
    this.player = document.createElement("audio");
    this.player.controls = true;
    this.player.preload = "metadata";
    this.player.src = this.mediaUrl;
    player.append(this._seekButton(-10), this.player, this._seekButton(10), this._closeButton());
    return player;
  }

  _closeButton() {
    const button = document.createElement("button");
    button.className = "row-action";
    button.innerHTML = '<ha-icon icon="mdi:close"></ha-icon><span>Chiudi</span>';
    button.setAttribute("aria-label", "Chiudi player");
    button.addEventListener("click", () => this.close());
    return button;
  }

  close() { this.release(); this.host.render(); }

  _seekButton(seconds) {
    const button = document.createElement("button");
    const forward = seconds > 0;
    button.className = "row-action";
    button.innerHTML = `<ha-icon icon="mdi:${forward ? "fast-forward" : "rewind"}-10"></ha-icon>`;
    button.setAttribute("aria-label", `${forward ? "Avanti" : "Indietro"} di 10 secondi`);
    button.addEventListener("click", () => {
      const limit = Number.isFinite(this.player.duration) ? this.player.duration : Infinity;
      this.player.currentTime = Math.max(0, Math.min(limit, this.player.currentTime + seconds));
    });
    return button;
  }

  release() {
    this.request += 1;
    if (this.mediaUrl) URL.revokeObjectURL(this.mediaUrl);
    this.mediaUrl = null;
    this.activeId = null;
    this.loadingId = null;
    this.player = null;
  }
}
