import assert from "node:assert/strict";
import test from "node:test";

import { RingAudioSession } from "../custom_components/media_bridge/frontend/ring-audio-session.js";

function media(label) {
  const track = { label, enabled: true, stopped: false, stop() { this.stopped = true; } };
  return { stream: { getAudioTracks: () => [track], getTracks: () => [track] }, track };
}

test("listen upgrades to full duplex without replacing the peer", async () => {
  const microphone = media("microphone");
  Object.defineProperty(globalThis, "navigator", {
    configurable: true,
    value: { mediaDevices: { getUserMedia: async () => microphone.stream } },
  });
  const states = [];
  const peer = { identity: "same-call" };
  const silent = media("silence");
  let oldReleased = false;
  let replacement = null;
  const session = new RingAudioSession({}, {}, {}, (state) => states.push(state));
  session.pc = peer;
  session.sender = { replaceTrack: async (track) => { replacement = track; } };
  session.localMedia = {
    stream: silent.stream,
    release: async () => { oldReleased = true; silent.track.stop(); },
  };
  session.mode = "listen";

  await session.switchMode("talk");

  assert.equal(session.pc, peer);
  assert.equal(session.mode, "talk");
  assert.equal(replacement, microphone.track);
  assert.equal(oldReleased, true);
  assert.equal(silent.track.stopped, true);
  assert.deepEqual(states.at(-1), { phase: "active", mode: "talk" });
});
