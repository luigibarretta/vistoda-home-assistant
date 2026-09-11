import assert from "node:assert/strict";
import test from "node:test";

import { BlinkWebRtcSession } from "../custom_components/media_bridge/frontend/blink-webrtc-session.js";

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

test("Blink ICE timeout proceeds when the offer embeds a usable candidate", async () => {
  const session = new BlinkWebRtcSession({}, {}, () => {});
  const peer = gatheringPeer("v=0\r\na=candidate:1 1 UDP 1 192.0.2.1 5000 typ host\r\n");

  await session.waitForIce(peer, 1);

  assert.equal(peer.listeners.size, 0);
});

test("Blink ICE timeout is fail-closed without an embedded candidate", async () => {
  const session = new BlinkWebRtcSession({}, {}, () => {});
  const peer = gatheringPeer("v=0\r\n");

  await assert.rejects(session.waitForIce(peer, 1), /Blink ICE gathering timed out/);

  assert.equal(peer.listeners.size, 0);
});

test("Blink ICE gathering completion clears listeners", async () => {
  const session = new BlinkWebRtcSession({}, {}, () => {});
  const peer = gatheringPeer("v=0\r\n");
  const waiting = session.waitForIce(peer, 100);
  peer.iceGatheringState = "complete";
  peer.listeners.get("icegatheringstatechange")();

  await waiting;

  assert.equal(peer.listeners.size, 0);
});
