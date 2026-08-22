import assert from "node:assert/strict";
import test from "node:test";

import { RingAudioSession } from "../custom_components/media_bridge/frontend/ring-audio-session.js";

function media(label) {
  const track = { label, enabled: true, stopped: false, stop() { this.stopped = true; } };
  return { stream: { getAudioTracks: () => [track], getTracks: () => [track] }, track };
}

function gatheringPeer(sdp) {
  const listeners = new Map();
  return {
    iceGatheringState: "gathering",
    localDescription: { sdp },
    addEventListener: (name, callback) => listeners.set(name, callback),
    removeEventListener: (name, callback) => {
      if (listeners.get(name) === callback) listeners.delete(name);
    },
    listeners,
  };
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

test("disabling the microphone returns to silence and releases capture", async () => {
  const session = new RingAudioSession({}, {}, {}, () => {});
  const microphone = media("microphone");
  const silence = media("silence");
  let replacement = null;
  session.pc = { identity: "same-call" };
  session.sender = { replaceTrack: async (track) => { replacement = track; } };
  session.localMedia = {
    stream: microphone.stream,
    release: async () => microphone.track.stop(),
  };
  session.mode = "talk";
  session.createMedia = async () => ({
    stream: silence.stream,
    release: async () => silence.track.stop(),
  });

  await session.switchMode("listen");

  assert.equal(session.mode, "listen");
  assert.equal(replacement, silence.track);
  assert.equal(microphone.track.stopped, true);
  assert.equal(session.pc.identity, "same-call");
});

test("ICE timeout proceeds when the SDP already has a usable candidate", async () => {
  const session = new RingAudioSession({}, {}, {}, () => {});
  const peer = gatheringPeer("v=0\r\na=candidate:1 1 UDP 1 192.0.2.1 5000 typ host\r\n");

  await session.waitForIce(peer, 1);

  assert.equal(peer.listeners.size, 0);
});

test("ICE timeout remains fail-closed when no candidate was gathered", async () => {
  const session = new RingAudioSession({}, {}, {}, () => {});
  const peer = gatheringPeer("v=0\r\n");

  await assert.rejects(session.waitForIce(peer, 1), /Raccolta ICE scaduta/);

  assert.equal(peer.listeners.size, 0);
});
