// HA chooses its audio-capable transport from ha-camera-stream.muted.
// Mutating only the nested <video> cannot select HLS when WebRTC lacks AAC.
export function setPlayerMuted(root, muted) {
  if (!root) return;
  if (["ha-camera-stream", "ha-hls-player", "ha-web-rtc-player", "video"].includes(root.localName)) {
    root.muted = muted;
    if (!muted && root.localName === "video") root.volume = 1;
  }
  if (!muted && root.localName === "ha-web-rtc-player") {
    // HA can omit incoming audio from srcObject when it arrives while muted.
    // Restore only this viewer's already-negotiated receiving tracks; never
    // acquire a microphone, create another peer or alter provider settings.
    const video = root.shadowRoot?.querySelector("video");
    const stream = video?.srcObject;
    if (stream?.getAudioTracks && stream?.addTrack) {
      for (const receiver of root._peerConnection?.getReceivers?.() || []) {
        const track = receiver.track;
        if (track?.kind === "audio" && track.readyState === "live" &&
            !stream.getAudioTracks().includes(track)) stream.addTrack(track);
      }
    }
  }
  if (root.shadowRoot) setPlayerMuted(root.shadowRoot, muted);
  for (const child of root.children || []) setPlayerMuted(child, muted);
}
