import assert from "node:assert/strict";
import test from "node:test";

import { BlinkWalnutSession } from "../custom_components/media_bridge/frontend/blink-walnut-session.js";
import { WalnutMicrophone } from "../custom_components/media_bridge/frontend/blink-walnut-microphone.js";

// Exercise the actual session/controller; stub only physical browser capture.
// No media devices, Home Assistant connection, or camera are used by these tests.
function harness(t) {
  t.mock.method(WalnutMicrophone.prototype, "prepare", async function () {
    this.echoCancellation = true;
    return true;
  });
  t.mock.method(WalnutMicrophone.prototype, "enable", function () {
    this.mutedAtEnable = this.owner.video.muted;
    this.active = true;
  });
  t.mock.method(WalnutMicrophone.prototype, "stop", function () {
    this.closed = true;
    this.active = false;
  });
  const schedule = globalThis.setTimeout;
  t.mock.method(globalThis, "setTimeout", (...args) => schedule(...args).unref());
  const controls = [];
  const states = [];
  const video = { muted: true, readyState: 2, play: async () => {} };
  const session = new BlinkWalnutSession({
    callWS: async (message) => { controls.push(message); },
  }, video, (state) => states.push(state));
  session.generation = 1;
  session.handle = "offline-test-session";
  session.supported = true;
  return { session, video, controls, states };
}

async function beginEnable(session) {
  const completion = session.toggleMicrophone();
  await new Promise(setImmediate);
  assert.ok(session.micAck, "capture must wait for the engine acknowledgement");
  assert.equal(session.capture.active, false);
  return { completion, capture: session.capture, request: session.micRequest };
}

async function acknowledge(session, pending) {
  await session._event({
    type: "microphone", enabled: true, request_id: pending.request,
  }, session.generation);
  await pending.completion;
  assert.equal(session.capture, pending.capture);
  assert.equal(session.microphone, true);
}

test("stale enable and disable acknowledgements cannot affect a new microphone epoch", async (t) => {
  const { session } = harness(t);
  const old = await beginEnable(session);
  await acknowledge(session, old);
  await session._disableMicrophone();
  const disabledRequest = session.micRequest;
  const current = await beginEnable(session);
  const acknowledgement = session.micAck;
  for (const event of [
    { enabled: true, request_id: old.request },
    { enabled: false, request_id: disabledRequest },
    { enabled: false, request_id: old.request },
  ]) {
    await session._event({ type: "microphone", ...event }, session.generation);
    assert.equal(session.micAck, acknowledgement);
    assert.equal(session.capture, current.capture);
    assert.equal(current.capture.active, false);
    assert.equal(current.capture.closed, false);
  }
  await acknowledge(session, current);
  await session._event({
    type: "microphone", enabled: false, request_id: current.request,
  }, session.generation);
  assert.equal(session.capture, null, "the matching epoch must still be revocable");
  assert.equal(current.capture.closed, true);
});

test("speaker toggled during pending enable is muted before half-duplex capture starts", async (t) => {
  const { session, video } = harness(t);
  session.streamAec = false;
  const pending = await beginEnable(session);
  await session.toggleSpeaker();
  assert.equal(session.speaker, true);
  assert.equal(video.muted, false, "listening is permitted before capture starts");
  await acknowledge(session, pending);
  assert.equal(pending.capture.mutedAtEnable, true);
  assert.equal(video.muted, true);
  assert.equal(session._duplex(), false);
});

test("AEC offer downgrade immediately suspends listening during active capture", async (t) => {
  const { session, video } = harness(t);
  session.streamAec = true;
  session.speaker = true;
  const pending = await beginEnable(session);
  await acknowledge(session, pending);
  assert.equal(video.muted, false);
  assert.equal(session._duplex(), true);
  await session._event({
    type: "audio_offer", supported: true, stream_aec: false,
  }, session.generation);
  assert.equal(video.muted, true);
  assert.equal(session._duplex(), false);
  assert.equal(session.capture, pending.capture);
  assert.equal(session.microphone, true);
});

test("late capture errors cannot revoke a replacement capture or another generation", async (t) => {
  const { session, controls } = harness(t);
  const old = await beginEnable(session);
  await acknowledge(session, old);
  await session._disableMicrophone();
  const current = await beginEnable(session);
  await acknowledge(session, current);
  const controlCount = controls.length;
  old.capture.onError(new Error("late old PCM send failure"));
  await new Promise(setImmediate);
  assert.equal(session.capture, current.capture);
  assert.equal(current.capture.closed, false);
  assert.equal(session.microphone, true);
  assert.equal(controls.length, controlCount);
  session.generation++;
  current.capture.onError(new Error("error from a previous session generation"));
  await new Promise(setImmediate);
  assert.equal(session.capture, current.capture);
  assert.equal(controls.length, controlCount);
});
