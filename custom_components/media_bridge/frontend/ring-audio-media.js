import { claimMicrophone } from "./microphone-coordinator.js";

export async function createRingAudioMedia(mode, owner) {
  if (mode === "talk") {
    const lease = await claimMicrophone(owner);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: false,
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      });
      let released = false;
      return { stream, release: async () => {
        if (released) return; released = true;
        stream.getTracks().forEach((track) => track.stop()); lease.release();
      } };
    } catch (error) {
      lease.release(); throw error;
    }
  }
  const context = new AudioContext();
  const destination = context.createMediaStreamDestination();
  const gain = context.createGain(); gain.gain.value = 0;
  const source = context.createConstantSource();
  source.connect(gain).connect(destination); source.start();
  let released = false;
  return {
    stream: destination.stream,
    release: async () => {
      if (released) return; released = true;
      try { source.stop(); } catch (_error) {}
      destination.stream.getTracks().forEach((track) => track.stop());
      await context.close();
    },
  };
}
