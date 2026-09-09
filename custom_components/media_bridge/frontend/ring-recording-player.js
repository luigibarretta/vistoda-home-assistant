export class RingRecordingPlayer {
  constructor(host) {
    this.host = host;
    this.activeId = null;
    this.loadingId = null;
    this.mediaUrl = null;
    this.player = null;
  }

  isOpen(recordingId) {
    return [this.activeId, this.loadingId].includes(recordingId);
  }

  async play(recording) {
    this.release();
    this.loadingId = recording.recording_id;
    this.host.render();
    try {
      const result = await this.host.hass.callWS({
        type: "media_bridge/ring/recordings/read",
        entry_id: this.host.entry.entry_id,
        recording_id: recording.recording_id,
      });
      const binary = atob(result.media_base64);
      const bytes = Uint8Array.from(binary, (character) => character.charCodeAt(0));
      this.mediaUrl = URL.createObjectURL(new Blob([bytes], { type: result.media_type }));
      this.activeId = recording.recording_id;
      this.host.status("");
    } catch (_error) {
      this.host.status("Riproduzione non disponibile.");
    } finally {
      this.loadingId = null;
      this.host.render();
      this.player?.play().catch(() => {});
    }
  }

  detail(recording) {
    const wrap = document.createElement("div");
    if (this.loadingId === recording.recording_id) {
      wrap.className = "hint";
      wrap.innerHTML = '<ha-icon icon="mdi:loading"></ha-icon> Caricamento audio…';
      return wrap;
    }
    const player = document.createElement("div");
    player.className = "player";
    this.player = document.createElement("audio");
    this.player.controls = true;
    this.player.preload = "metadata";
    this.player.src = this.mediaUrl;
    player.append(this._seekButton(-10), this.player, this._seekButton(10));
    return player;
  }

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
    if (this.mediaUrl) URL.revokeObjectURL(this.mediaUrl);
    this.mediaUrl = null;
    this.activeId = null;
    this.player = null;
  }
}
