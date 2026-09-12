// Capture-only worklet: never connects microphone samples to local speakers.
class BlinkPcmCapture extends AudioWorkletProcessor {
  constructor() { super(); this.phase = 0; this.sum = 0; this.count = 0; this.offset = 0; this.frame = new Int16Array(512); }
  process(inputs) {
    const input = inputs[0]?.[0];
    if (!input) return true;
    for (const sample of input) {
      this.sum += sample; this.count++; this.phase += 16000 / sampleRate;
      if (this.phase >= 1) {
        this.phase -= 1;
        const value = Math.max(-1, Math.min(1, this.sum / this.count));
        this.frame[this.offset++] = Math.round(value * (value < 0 ? 32768 : 32767));
        this.sum = 0; this.count = 0;
        if (this.offset === 512) {
          this.port.postMessage({ samples: this.frame.buffer, capturedAt: currentTime }, [this.frame.buffer]);
          this.frame = new Int16Array(512); this.offset = 0;
        }
      }
    }
    return true;
  }
}
registerProcessor("blink-pcm-capture", BlinkPcmCapture);
