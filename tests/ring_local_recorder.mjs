import assert from "node:assert/strict";
import test from "node:test";

import {
  RingLocalRecorder,
  bytesToBase64,
} from "../custom_components/media_bridge/frontend/ring-local-recorder.js";

class Node {
  connect(target) { this.target = target; }
  disconnect() { this.disconnected = true; }
}

class Context {
  async resume() {}
  createMediaStreamDestination() { return { stream: media("mixed"), getAudioTracks: () => [] }; }
  createMediaStreamSource() { return new Node(); }
  async close() { this.closed = true; }
}

class Recorder {
  static isTypeSupported(value) { return value.startsWith("audio/webm"); }
  constructor(_stream, options) {
    this.mimeType = options.mimeType;
    this.state = "inactive";
    this.listeners = new Map();
  }
  addEventListener(name, callback) { this.listeners.set(name, callback); }
  start() { this.state = "recording"; }
  stop() {
    this.state = "inactive";
    this.listeners.get("stop")?.();
  }
}

function media(label) {
  const track = { label, stop() { this.stopped = true; } };
  return {
    getAudioTracks: () => [track],
    getTracks: () => [track],
  };
}

test("local recorder mixes, uploads and preserves bounded metadata", async () => {
  const calls = [];
  const states = [];
  const recorder = new RingLocalRecorder(
    { callWS: async (message) => { calls.push(message); return { recording_id: "saved" }; } },
    { entry_id: "ring-entry" },
    (state) => states.push(state),
    { AudioContext: Context, MediaRecorder: Recorder },
  );
  await recorder.start(media("remote"), media("microphone"), true);
  recorder.collect(new Blob([new Uint8Array(1024)], { type: "audio/webm" }));
  const result = await recorder.stop(true);

  assert.equal(result.recording_id, "saved");
  assert.equal(calls[0].type, "media_bridge/ring/recordings/upload");
  assert.equal(calls[0].entry_id, "ring-entry");
  assert.equal(calls[0].media_type, "audio/webm;codecs=opus");
  assert.ok(calls[0].media_base64.length > 1000);
  assert.deepEqual(states, ["recording", "uploading", "saved"]);
});

test("base64 conversion is chunk-safe", () => {
  assert.equal(bytesToBase64(new Uint8Array([1, 2, 3, 4])), "AQIDBA==");
});
