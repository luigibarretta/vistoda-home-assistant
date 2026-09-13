import { copy } from "./panel-copy.js";

export function configureRingMedia(session, pc) {
  const media = session.localMedia.stream;
  const audio = pc.addTransceiver(media.getAudioTracks()[0], { direction:"sendrecv", streams:[media] });
  const pcmu = RTCRtpSender.getCapabilities("audio")?.codecs.filter(c => c.mimeType.toLowerCase() === "audio/pcmu");
  if (!pcmu?.length) throw new Error(copy(session, "PCMU non supportato dal browser"));
  audio.setCodecPreferences(pcmu);
  if (session.entry.camera_id) {
    const h264 = RTCRtpReceiver.getCapabilities("video")?.codecs.filter(c => c.mimeType.toLowerCase() === "video/h264");
    if (!h264?.length) throw new Error(copy(session, "H264 non supportato dal browser"));
    pc.addTransceiver("video", { direction:"recvonly" }).setCodecPreferences(h264);
  }
  return audio.sender;
}

export function ringSessionRequest(entry, action) {
  return { type:`media_bridge/ring/${entry.camera_id ? "camera/" : ""}session/${action}`,
    entry_id:entry.entry_id, ...(entry.camera_id ? { camera_id:entry.camera_id } : {}) };
}
