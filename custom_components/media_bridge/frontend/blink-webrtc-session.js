import { blinkWebRtcMicrophone } from "./blink-webrtc-microphone.js";

const OFFER_ICE_TIMEOUT_MS = 8000;
const MAX_ICE_CANDIDATES = 256;

export class BlinkWebRtcSession {
  constructor(hass, video, onState) {
    this.hass = hass;
    this.video = video;
    this.onState = onState;
    this.pc = null;
    this.handle = null;
    this.unsubscribe = null;
    this.localTrack = null;
    this.micLease = null;
    this.pendingMicLease = null;
    this.micPending = false;
    this.micCooldownUntil = 0;
    this.remoteStream = null;
    this.pendingLocalIce = [];
    this.pendingRemoteIce = [];
    this.generation = 0;
    this.microphone = false;
    this.speaker = false;
    this.stopping = null;
    this.restartAttempts = 0;
  }

  async start(alias) {
    if (this.pc) return;
    const generation = ++this.generation;
    this.alias = alias;
    this.onState({ phase: "starting", message: "Preparazione WebRTC Blink…" });
    try {
      const pc = new RTCPeerConnection({
        iceServers: [], bundlePolicy: "balanced", rtcpMuxPolicy: "require", iceCandidatePoolSize: 4,
      });
      this.pc = pc;
      pc.ontrack = (event) => this._play(event, generation);
      pc.onicecandidate = (event) => { if (event.candidate) this._localIce(event.candidate); };
      pc.onconnectionstatechange = () => this._connectionChanged(generation);
      pc.oniceconnectionstatechange = () => {
        if (pc.iceConnectionState === "failed") this._restartIce(generation);
      };
      pc.addTransceiver("audio", { direction: "sendrecv" });
      pc.addTransceiver("video", { direction: "recvonly" });
      await pc.setLocalDescription(await pc.createOffer());
      await this.waitForIce(pc);
      if (generation !== this.generation) return;
      const unsubscribe = await this.hass.connection.subscribeMessage(
        (event) => this._event(event, generation).catch(async (error) => {
          if (generation !== this.generation) return;
          await this.stop(false);
          this.onState({ phase: "error", message: error?.message || "Segnalazione Blink non valida" });
        }),
        { type: "blink_live_bridge/webrtc/subscribe", alias,
          offer_sdp: pc.localDescription.sdp },
      );
      if (generation !== this.generation) {
        await Promise.resolve(unsubscribe()).catch(() => {}); return;
      }
      this.unsubscribe = unsubscribe;
      this.onState({ phase: "connecting", message: "Connessione alla telecamera…" });
    } catch (error) {
      if (generation !== this.generation) return;
      await this.stop(false);
      const fallback = error?.code === "legacy_required";
      this.onState({ phase: fallback ? "fallback" : "error",
        reason: fallback ? "no_ring_device_id" : undefined,
        message: fallback ? "Passaggio al live Blink compatibile" :
          error?.message || "Live Blink non disponibile" });
    }
  }

  async toggleSpeaker() {
    if (!this.handle || !this.pc) return;
    const generation = this.generation;
    const enabled = !this.speaker;
    try { await this._control("speaker", { enabled }); }
    catch (_error) { return this._state("active", "Comando audio non riuscito"); }
    if (generation !== this.generation || !this.pc) return;
    this.speaker = enabled;
    this.video.muted = !enabled;
    if (enabled) await this.video.play().catch(() => {});
    this._state("active", enabled ? "Audio della telecamera attivo" : "Audio disattivato");
  }

  stop(notify = true) {
    if (this.stopping) return this.stopping;
    this.stopping = this._stop(notify).finally(() => { this.stopping = null; });
    return this.stopping;
  }

  async _stop(notify) {
    ++this.generation;
    const handle = this.handle; this.handle = null;
    const unsubscribe = this.unsubscribe; this.unsubscribe = null;
    const pc = this.pc; this.pc = null; pc?.close();
    const remoteStream = this.remoteStream; this.remoteStream = null;
    const track = this.localTrack; this.localTrack = null;
    if (track) { track.enabled = false; track.stop(); }
    this.pendingMicLease?.release(); this.pendingMicLease = null;
    this.micLease?.release(); this.micLease = null;
    this.microphone = false; this.speaker = false; this.micPending = false;
    this.pendingLocalIce = []; this.pendingRemoteIce = [];
    if (this.video.srcObject === remoteStream) {
      this.video.pause(); this.video.srcObject = null; this.video.muted = true;
    }
    if (notify) this.onState({ phase: "idle", microphone: false, speaker: false,
      message: "Live terminato" });
    const cleanup = [];
    if (handle) cleanup.push(this.hass.callWS({ type: "blink_live_bridge/webrtc/control",
      session_id: handle, action: "stop" }));
    if (unsubscribe) cleanup.push(Promise.resolve(unsubscribe()));
    await Promise.race([
      Promise.allSettled(cleanup),
      new Promise((resolve) => setTimeout(resolve, 3000)),
    ]);
  }

  async _event(event, generation) {
    if (generation !== this.generation || !this.pc) return;
    if (event.type === "ready") {
      this.handle = event.session_id;
      const pending = this.pendingLocalIce.splice(0);
      for (const candidate of pending) await this._sendIce(candidate);
    } else if (event.type === "answer") {
      if (event.sdp.includes("a=e2ee-content-encryption-mode:")) {
        throw new Error("Modalità E2EE Blink non supportata");
      }
      await this.pc.setRemoteDescription({ type: "answer", sdp: event.sdp });
      if (generation !== this.generation || !this.pc) return;
      for (const candidate of this.pendingRemoteIce.splice(0)) await this.pc.addIceCandidate(candidate);
      if (generation !== this.generation || !this.pc) return;
      await this._control("activate");
    } else if (event.type === "ice") {
      const candidate = { candidate: event.candidate, sdpMid: event.sdp_mid,
        sdpMLineIndex: event.sdp_mline_index };
      if (this.pc.remoteDescription) await this.pc.addIceCandidate(candidate);
      else if (this.pendingRemoteIce.length < MAX_ICE_CANDIDATES) this.pendingRemoteIce.push(candidate);
      else throw new Error("Troppi candidati ICE Blink");
    } else if (event.type === "ice_restart") {
      await this._restartIce(generation);
    } else if (event.type === "mic_overridden") {
      await this._disableMicrophone(false);
      if (generation !== this.generation || !this.pc) return;
      this.micCooldownUntil = performance.now() + Math.max(0, event.cooldown_ms || 0);
      const seconds = Math.ceil((event.cooldown_ms || 0) / 1000);
      this._state("active", `Microfono disattivato da un’altra sessione${seconds ? ` per ${seconds}s` : ""}`);
    } else if (event.type === "fallback") {
      await this.stop(false); this.onState({ phase: "fallback", reason: event.reason,
        message: event.message || "Passaggio al live Blink compatibile" });
    } else if (event.type === "error" || event.type === "closed") {
      const message = event.message || "Sessione Blink terminata";
      await this.stop(false); this.onState({ phase: "error", message, providerCode: event.code });
    }
  }

  _localIce(candidate) {
    if (!this.handle && this.pendingLocalIce.length < MAX_ICE_CANDIDATES) {
      this.pendingLocalIce.push(candidate);
    }
    else this._sendIce(candidate).catch(() => this.stop());
  }

  _sendIce(candidate) {
    return this._control("ice", { candidate: candidate.candidate,
      sdp_mid: candidate.sdpMid, sdp_mline_index: candidate.sdpMLineIndex || 0 });
  }

  _control(action, values = {}) {
    if (!this.handle) return Promise.resolve();
    return this.hass.callWS({ type: "blink_live_bridge/webrtc/control",
      session_id: this.handle, action, ...values });
  }

  waitForIce(pc, timeoutMs = OFFER_ICE_TIMEOUT_MS) {
    if (pc.iceGatheringState === "complete") return Promise.resolve();
    return new Promise((resolve, reject) => {
      let settled = false;
      const finish = (error) => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        pc.removeEventListener("icegatheringstatechange", gatheringChanged);
        pc.removeEventListener("icecandidate", candidateChanged);
        if (error) reject(error); else resolve();
      };
      const gatheringChanged = () => {
        if (pc.iceGatheringState === "complete") finish();
      };
      const candidateChanged = (event) => {
        if (!event.candidate) finish();
      };
      pc.addEventListener("icegatheringstatechange", gatheringChanged);
      pc.addEventListener("icecandidate", candidateChanged);
      const timer = setTimeout(() => {
        const hasCandidate = /^a=candidate:/m.test(pc.localDescription?.sdp ?? "");
        finish(hasCandidate ? null : new Error("Raccolta ICE Blink scaduta"));
      }, timeoutMs);
      gatheringChanged();
    });
  }

  async _play(event, generation) {
    if (generation !== this.generation) return;
    this.remoteStream ||= new MediaStream();
    if (!this.remoteStream.getTracks().some((track) => track.id === event.track.id)) {
      this.remoteStream.addTrack(event.track);
    }
    this.video.srcObject = this.remoteStream; this.video.muted = !this.speaker;
    await this.video.play().catch(() => {});
  }

  _connectionChanged(generation) {
    if (generation !== this.generation) return;
    if (this.pc?.connectionState === "connected") this._state("active", "Live WebRTC connesso");
    if (this.pc?.connectionState === "failed") this._restartIce(generation);
    if (this.pc?.connectionState === "closed") this.stop();
  }

  async _restartIce(generation) {
    if (generation !== this.generation || !this.pc || this.restartAttempts >= 1) return;
    this.restartAttempts += 1;
    this.onState({ phase: "connecting", message: "Ripristino connessione WebRTC…" });
    try {
      await this.pc.setLocalDescription(await this.pc.createOffer({ iceRestart: true }));
      if (generation !== this.generation || !this.pc) return;
      await this._control("sdp", { offer_sdp: this.pc.localDescription.sdp,
        reason: "ice_restart" });
    } catch (_error) { await this.stop(); }
  }

  _state(phase, message) {
    this.onState({ phase, message, microphone: this.microphone, speaker: this.speaker,
      microphonePending: this.micPending });
  }
}

Object.assign(BlinkWebRtcSession.prototype, blinkWebRtcMicrophone);
