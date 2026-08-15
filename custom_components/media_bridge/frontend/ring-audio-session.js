const STUN = "stun:stun.kinesisvideo.us-east-1.amazonaws.com:443";
const COOLDOWN_MS = 10_500;

export class RingAudioSession {
  constructor(hass, entry, audio, onState) {
    this.hass = hass;
    this.entry = entry;
    this.audio = audio;
    this.onState = onState;
    this.pc = null;
    this.sender = null;
    this.remoteId = null;
    this.localMedia = null;
    this.mode = null;
    this.expiry = null;
    this.cooldown = null;
    this.cooldownUntil = 0;
    this.busy = false;
    this.stopping = null;
  }

  async start(mode) {
    if (this.busy) return;
    if (this.pc) return this.switchMode(mode);
    if (Date.now() < this.cooldownUntil) return;
    this.busy = true;
    this.onState({ phase: "starting", mode });
    try {
      this.localMedia = await this.createMedia(mode);
      const pc = new RTCPeerConnection({ iceServers: [{ urls: STUN }] });
      this.pc = pc;
      pc.ontrack = (event) => this.play(event);
      pc.onconnectionstatechange = () => this.connectionChanged();
      const transceiver = pc.addTransceiver(this.localMedia.stream.getAudioTracks()[0], {
        direction: "sendrecv",
        streams: [this.localMedia.stream],
      });
      this.sender = transceiver.sender;
      const pcmu = RTCRtpSender.getCapabilities("audio")?.codecs.filter(
        (codec) => codec.mimeType.toLowerCase() === "audio/pcmu",
      );
      if (!pcmu?.length) throw new Error("PCMU non supportato dal browser");
      transceiver.setCodecPreferences(pcmu);
      await pc.setLocalDescription(await pc.createOffer());
      await this.waitForIce(pc);
      this.onState({ phase: "connecting", mode });
      const result = await this.hass.callWS({
        type: "media_bridge/ring/session/create",
        entry_id: this.entry.entry_id,
        offer_sdp: pc.localDescription.sdp,
        mode,
      });
      this.remoteId = result.session_id;
      this.mode = mode;
      await pc.setRemoteDescription({ type: "answer", sdp: result.answer_sdp });
      for (const ice of result.ice_candidates) {
        await pc.addIceCandidate({
          candidate: ice.candidate,
          sdpMLineIndex: ice.sdp_mline_index,
        });
      }
      this.expiry = setTimeout(() => this.stop("Sessione scaduta"), result.expires_in * 1000);
      this.onState({ phase: "active", mode });
    } catch (error) {
      await this.deleteRemote();
      this.disposePeer();
      if (error?.code === "cooldown") {
        this.cooldownUntil = Date.now() + COOLDOWN_MS;
        this.startCooldown("Ring sta chiudendo la sessione precedente");
      } else {
        this.onState({ phase: "error", message: error?.message || "Audio Ring non disponibile" });
      }
    } finally {
      this.busy = false;
    }
  }

  async switchMode(mode) {
    if (this.busy || !this.sender || mode === this.mode) return;
    this.busy = true;
    this.onState({ phase: "switching", mode });
    let next;
    try {
      next = await this.createMedia(mode);
      await this.sender.replaceTrack(next.stream.getAudioTracks()[0]);
      const previous = this.localMedia;
      this.localMedia = next;
      this.mode = mode;
      await previous?.release();
      this.onState({ phase: "active", mode });
    } catch (error) {
      await next?.release();
      this.onState({
        phase: "active",
        mode: this.mode,
        message: error?.message || "Cambio modalità non riuscito",
      });
    } finally {
      this.busy = false;
    }
  }

  async createMedia(mode) {
    if (mode === "talk") {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: false,
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      });
      return { stream, release: async () => stream.getTracks().forEach((track) => track.stop()) };
    }
    const context = new AudioContext();
    const destination = context.createMediaStreamDestination();
    const gain = context.createGain();
    gain.gain.value = 0;
    const source = context.createConstantSource();
    source.connect(gain).connect(destination);
    source.start();
    return {
      stream: destination.stream,
      release: async () => {
        try { source.stop(); } catch (_error) {}
        destination.stream.getTracks().forEach((track) => track.stop());
        await context.close();
      },
    };
  }

  waitForIce(pc) {
    if (pc.iceGatheringState === "complete") return Promise.resolve();
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error("Raccolta ICE scaduta")), 8000);
      pc.addEventListener("icegatheringstatechange", () => {
        if (pc.iceGatheringState === "complete") { clearTimeout(timer); resolve(); }
      });
    });
  }

  async play(event) {
    this.audio.srcObject = event.streams[0] || new MediaStream([event.track]);
    try { await this.audio.play(); } catch (_error) {
      this.onState({ phase: "active", mode: this.mode, message: "Tocca un controllo per l’audio" });
    }
  }

  connectionChanged() {
    const state = this.pc?.connectionState;
    if (state === "connected") this.onState({ phase: "active", mode: this.mode });
    if (["failed", "closed"].includes(state)) this.stop("Connessione terminata");
  }

  toggleMute() {
    const track = this.localMedia?.stream.getAudioTracks()[0];
    if (!track || this.mode !== "talk") return true;
    track.enabled = !track.enabled;
    return !track.enabled;
  }

  stop(message = "Sessione terminata") {
    if (this.stopping) return this.stopping;
    this.stopping = this.performStop(message).finally(() => { this.stopping = null; });
    return this.stopping;
  }

  async performStop(message) {
    const hadSession = Boolean(this.remoteId);
    await this.deleteRemote();
    this.disposePeer();
    if (!hadSession) return this.onState({ phase: "idle", message });
    this.cooldownUntil = Date.now() + COOLDOWN_MS;
    this.startCooldown(message);
  }

  async deleteRemote() {
    const id = this.remoteId;
    this.remoteId = null;
    if (!id) return;
    try {
      await this.hass.callWS({
        type: "media_bridge/ring/session/delete",
        entry_id: this.entry.entry_id,
        session_id: id,
      });
    } catch (_error) {}
  }

  disposePeer() {
    clearTimeout(this.expiry);
    const pc = this.pc;
    this.pc = null;
    pc?.close();
    this.sender = null;
    this.localMedia?.release();
    this.localMedia = null;
    this.audio.srcObject = null;
    this.mode = null;
  }

  startCooldown(message) {
    clearInterval(this.cooldown);
    const tick = () => {
      const seconds = Math.max(0, Math.ceil((this.cooldownUntil - Date.now()) / 1000));
      if (seconds === 0) {
        clearInterval(this.cooldown);
        this.cooldown = null;
        this.onState({ phase: "idle", message: "Pronto per una nuova sessione" });
      } else this.onState({ phase: "cooldown", seconds, message });
    };
    tick();
    this.cooldown = setInterval(tick, 250);
  }

  async destroy() {
    await this.stop();
    clearInterval(this.cooldown);
    this.cooldown = null;
  }
}
