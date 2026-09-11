import { copy } from "./panel-copy.js";
import { claimMicrophone } from "./microphone-coordinator.js";

export const blinkWebRtcMicrophone = {
  async toggleMicrophone() {
    if (this.microphone) return this._disableMicrophone(true);
    if (!this.handle || !this.pc || this.micPending) return;
    if (performance.now() < this.micCooldownUntil) {
      const seconds = Math.ceil((this.micCooldownUntil - performance.now()) / 1000);
      return this._state("active", copy(this, "Microfono disponibile tra {p0}s", { p0: seconds }));
    }
    const generation = this.generation;
    this.micPending = true; this._state("active", copy(this, "Autorizzazione microfono…"));
    let lease = null; let track = null; let sender = null;
    try {
      lease = await claimMicrophone(this);
      if (generation !== this.generation || !this.pc) { lease.release(); return; }
      this.pendingMicLease = lease;
      const stream = await navigator.mediaDevices.getUserMedia({
        video: false,
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      });
      track = stream.getAudioTracks()[0];
      if (generation !== this.generation || !this.pc || this.pendingMicLease !== lease) {
        stream.getTracks().forEach((item) => item.stop()); lease.release(); return;
      }
      if (!track) throw new Error(copy(this, "Microfono non disponibile"));
      this.micLease = lease; this.pendingMicLease = null; this.localTrack = track;
      sender = this.pc.getTransceivers().find((item) => item.receiver.track.kind === "audio")?.sender;
      await sender?.replaceTrack(track);
      if (generation !== this.generation || this.localTrack !== track) {
        await this._discardMic(track, lease, sender); return;
      }
      await this._control("microphone", { enabled: true });
      if (generation !== this.generation || this.localTrack !== track) {
        await this._discardMic(track, lease, sender); return;
      }
      this.micPending = false; this.microphone = true;
      this._state("active", copy(this, "Microfono attivo"));
    } catch (error) {
      await this._discardMic(track, lease, sender);
      if (generation !== this.generation) return;
      await this._disableMicrophone(false);
      this._state("active", error?.message || copy(this, "Impossibile attivare il microfono"));
    }
  },

  async _disableMicrophone(notifyProvider) {
    const generation = this.generation;
    const pending = this.pendingMicLease; this.pendingMicLease = null; pending?.release();
    const track = this.localTrack; this.localTrack = null;
    if (track) { track.enabled = false; track.stop(); }
    const lease = this.micLease; this.micLease = null; lease?.release();
    this.microphone = false; this.micPending = true;
    const sender = this.pc?.getTransceivers().find(
      (item) => item.receiver.track.kind === "audio")?.sender;
    await sender?.replaceTrack(null).catch(() => {});
    if (notifyProvider && this.handle) {
      await this._control("microphone", { enabled: false }).catch(() => {});
    }
    if (generation !== this.generation) return;
    this.micPending = false;
    if (notifyProvider && this.pc) this._state("active", copy(this, "Microfono disattivato"));
  },

  async _discardMic(track, lease, sender) {
    if (this.localTrack === track) this.localTrack = null;
    if (this.micLease === lease) this.micLease = null;
    if (this.pendingMicLease === lease) this.pendingMicLease = null;
    track?.stop(); lease?.release();
    if (sender?.track === track) await sender.replaceTrack(null).catch(() => {});
  },
};
