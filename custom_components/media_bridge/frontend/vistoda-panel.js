const STUN = "stun:stun.kinesisvideo.us-east-1.amazonaws.com:443";

class VistodaPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._mounted = false;
    this._pc = null;
    this._session = null;
    this._localStream = null;
    this._audioContext = null;
    this._silentSource = null;
    this._expiry = null;
  }

  set hass(value) {
    this._hass = value;
    if (!this._mounted) this._mount();
  }

  set panel(value) {
    this._panel = value;
  }

  async _mount() {
    this._mounted = true;
    this.shadowRoot.innerHTML = `
      <style>
        :host { display:block; min-height:100%; color:var(--primary-text-color); }
        main { box-sizing:border-box; max-width:760px; margin:0 auto; padding:28px 18px 48px; }
        header { display:flex; align-items:center; gap:14px; margin-bottom:22px; }
        .mark { display:grid; place-items:center; width:52px; height:52px; border-radius:18px;
          background:linear-gradient(145deg,#6246ea,#27b3a2); color:white; font-size:27px; }
        h1 { font-size:26px; margin:0; } header p { margin:3px 0 0; color:var(--secondary-text-color); }
        .card { padding:22px; border-radius:22px; background:var(--card-background-color);
          box-shadow:var(--ha-card-box-shadow); border:1px solid var(--divider-color); }
        .device { display:flex; justify-content:space-between; gap:16px; align-items:start; }
        h2 { margin:0 0 7px; font-size:20px; } .hint { color:var(--secondary-text-color); line-height:1.45; }
        .badge { border-radius:999px; padding:7px 11px; font-weight:600; white-space:nowrap;
          background:color-mix(in srgb,var(--success-color,#43a047) 18%,transparent); }
        .badge.off { background:color-mix(in srgb,var(--error-color,#db4437) 16%,transparent); }
        .status { display:flex; align-items:center; gap:9px; min-height:24px; margin:22px 0 14px; }
        .dot { width:10px; height:10px; border-radius:50%; background:var(--secondary-text-color); }
        .dot.live { background:var(--success-color,#43a047); box-shadow:0 0 0 5px #43a04725; }
        .actions { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px; }
        button { min-height:48px; border:0; border-radius:14px; padding:10px 14px; cursor:pointer;
          font:inherit; font-weight:650; color:var(--primary-text-color); background:var(--secondary-background-color); }
        button.primary { color:white; background:linear-gradient(135deg,#6246ea,#4967e9); }
        button.talk { color:white; background:linear-gradient(135deg,#d84d75,#f47740); }
        button:disabled { opacity:.45; cursor:not-allowed; }
        .privacy { margin:18px 0 0; padding-top:16px; border-top:1px solid var(--divider-color);
          color:var(--secondary-text-color); font-size:14px; line-height:1.45; }
        audio { width:100%; height:0; display:block; }
        @media (max-width:520px) { main{padding:18px 12px 36px}.card{padding:18px}.actions{grid-template-columns:1fr} }
      </style>
      <main>
        <header><div class="mark">◉</div><div><h1>Vistoda</h1><p>Citofono privato, senza cloud esposto</p></div></header>
        <section class="card">
          <div class="device"><div><h2>Ring Intercom</h2><div class="hint">Audio live bidirezionale · sessione massima 2 minuti</div></div><span class="badge off" id="availability">Verifica…</span></div>
          <div class="status"><span class="dot" id="dot"></span><span id="status">Pronto</span></div>
          <div class="actions">
            <button class="primary" id="listen">Ascolta</button>
            <button class="talk" id="talk">Parla</button>
            <button id="mute" hidden>Disattiva microfono</button>
            <button id="stop" disabled>Termina</button>
          </div>
          <p class="privacy">“Ascolta” invia soltanto silenzio tecnico. “Parla” chiede il permesso del microfono al browser: Vistoda non lo attiva mai automaticamente e non registra l’audio.</p>
          <audio id="remote" autoplay></audio>
        </section>
      </main>`;
    this.$ = (id) => this.shadowRoot.getElementById(id);
    this.$("listen").addEventListener("click", () => this._start("listen"));
    this.$("talk").addEventListener("click", () => this._start("talk"));
    this.$("stop").addEventListener("click", () => this._stop());
    this.$("mute").addEventListener("click", () => this._toggleMute());
    await this._loadEntry();
  }

  async _loadEntry() {
    try {
      const result = await this._hass.callWS({ type: "media_bridge/ring/info" });
      this._entry = result.entries[0] || null;
      const badge = this.$("availability");
      badge.textContent = this._entry?.available ? "Disponibile" : "Non disponibile";
      badge.classList.toggle("off", !this._entry?.available);
      this._setButtons(!this._entry?.available);
      if (!this._entry) this._status("Nessun bridge Ring configurato");
    } catch (_error) {
      this._status("Impossibile leggere Vistoda");
      this._setButtons(true);
    }
  }

  async _start(mode) {
    if (!this._entry || this._pc) return;
    this._setButtons(true);
    this._status(mode === "talk" ? "Autorizza il microfono…" : "Preparazione ascolto…");
    try {
      const stream = mode === "talk" ? await this._microphone() : await this._silence();
      this._localStream = stream;
      const pc = new RTCPeerConnection({ iceServers: [{ urls: STUN }] });
      this._pc = pc;
      pc.ontrack = (event) => this._play(event);
      pc.onconnectionstatechange = () => this._connectionChanged();
      const transceiver = pc.addTransceiver(stream.getAudioTracks()[0], {
        direction: "sendrecv",
        streams: [stream],
      });
      const pcmu = RTCRtpSender.getCapabilities("audio")?.codecs.filter(
        (codec) => codec.mimeType.toLowerCase() === "audio/pcmu",
      );
      if (!pcmu?.length) throw new Error("PCMU non supportato dal browser");
      transceiver.setCodecPreferences(pcmu);
      await pc.setLocalDescription(await pc.createOffer());
      await this._waitForIce(pc);
      this._status("Connessione a Ring…");
      const result = await this._hass.callWS({
        type: "media_bridge/ring/session/create",
        entry_id: this._entry.entry_id,
        offer_sdp: pc.localDescription.sdp,
        mode,
      });
      this._session = result.session_id;
      this._mode = mode;
      await pc.setRemoteDescription({ type: "answer", sdp: result.answer_sdp });
      for (const ice of result.ice_candidates) {
        await pc.addIceCandidate({
          candidate: ice.candidate,
          sdpMLineIndex: ice.sdp_mline_index,
        });
      }
      this.$("stop").disabled = false;
      this.$("mute").hidden = mode !== "talk";
      this._expiry = setTimeout(() => this._stop("Sessione scaduta"), result.expires_in * 1000);
    } catch (error) {
      await this._cleanupRemote();
      this._dispose();
      this._status(error?.message || "Audio Ring non disponibile");
      this._setButtons(false);
    }
  }

  async _microphone() {
    return navigator.mediaDevices.getUserMedia({
      video: false,
      audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
    });
  }

  async _silence() {
    this._audioContext = new AudioContext();
    const destination = this._audioContext.createMediaStreamDestination();
    const gain = this._audioContext.createGain();
    gain.gain.value = 0;
    this._silentSource = this._audioContext.createConstantSource();
    this._silentSource.connect(gain).connect(destination);
    this._silentSource.start();
    return destination.stream;
  }

  _waitForIce(pc) {
    if (pc.iceGatheringState === "complete") return Promise.resolve();
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error("Raccolta ICE scaduta")), 8000);
      pc.addEventListener("icegatheringstatechange", () => {
        if (pc.iceGatheringState === "complete") { clearTimeout(timer); resolve(); }
      });
    });
  }

  async _play(event) {
    const stream = event.streams[0] || new MediaStream([event.track]);
    this.$("remote").srcObject = stream;
    try { await this.$("remote").play(); } catch (_error) { this._status("Tocca Parla o Ascolta per l’audio"); }
  }

  _connectionChanged() {
    const state = this._pc?.connectionState;
    if (state === "connected") this._status(this._mode === "talk" ? "Conversazione attiva" : "Ascolto attivo", true);
    if (["failed", "closed"].includes(state)) this._stop("Connessione terminata");
  }

  _toggleMute() {
    const track = this._localStream?.getAudioTracks()[0];
    if (!track) return;
    track.enabled = !track.enabled;
    this.$("mute").textContent = track.enabled ? "Disattiva microfono" : "Riattiva microfono";
  }

  async _stop(message = "Sessione terminata") {
    await this._cleanupRemote();
    this._dispose();
    this._status(message);
    this._setButtons(!this._entry?.available);
  }

  async _cleanupRemote() {
    const id = this._session;
    this._session = null;
    if (!id || !this._entry) return;
    try { await this._hass.callWS({ type:"media_bridge/ring/session/delete", entry_id:this._entry.entry_id, session_id:id }); } catch (_error) {}
  }

  _dispose() {
    clearTimeout(this._expiry);
    this._pc?.close(); this._pc = null;
    this._localStream?.getTracks().forEach((track) => track.stop()); this._localStream = null;
    try { this._silentSource?.stop(); } catch (_error) {}
    this._silentSource = null;
    this._audioContext?.close(); this._audioContext = null;
    this.$("remote").srcObject = null;
    this.$("mute").hidden = true;
    this.$("stop").disabled = true;
  }

  _status(text, live = false) { this.$("status").textContent = text; this.$("dot").classList.toggle("live", live); }
  _setButtons(disabled) { this.$("listen").disabled = disabled; this.$("talk").disabled = disabled; }
  disconnectedCallback() { if (this._pc) this._stop(); }
}

customElements.define("vistoda-panel", VistodaPanel);
