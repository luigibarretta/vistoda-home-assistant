import assert from "node:assert/strict";
import test from "node:test";
import { BlinkWalnutSession } from "../custom_components/media_bridge/frontend/blink-walnut-session.js";
import { WalnutMicrophone } from "../custom_components/media_bridge/frontend/blink-walnut-microphone.js";

function harness(t) {
  t.mock.method(WalnutMicrophone.prototype, "prepare", async () => true);
  t.mock.method(WalnutMicrophone.prototype, "enable", function () {
    this.mutedAtEnable = this.owner.video.muted; this.active = true;
  });
  t.mock.method(WalnutMicrophone.prototype, "stop", function () { this.closed = true; this.active = false; });
  const schedule = globalThis.setTimeout;
  t.mock.method(globalThis, "setTimeout", (...args) => schedule(...args).unref());
  const controls = []; const states = [];
  const video = Object.assign(new EventTarget(), { localName: "video", muted: false, readyState: 2,
    play: async () => {}, children: [] });
  const host = { children: [video] };
  const session = new BlinkWalnutSession({ callWS: async (message) => controls.push(message) },
    host, (state) => states.push(state));
  session.generation = 1; session.closed = false; session.handle = "offline-session"; session.supported = true;
  return { session, video, host, controls, states };
}
async function begin(session) {
  const completion = session.toggleMicrophone(); await new Promise(setImmediate);
  assert.ok(session.micAck); assert.equal(session.capture.active, false);
  return { completion, capture: session.capture, request: session.micRequest };
}
async function ack(session, pending) {
  await session._event({ type: "microphone", enabled: true, request_id: pending.request }, session.generation);
  await pending.completion; assert.equal(session.microphone, true);
}
test("talk waits for the exact ACK, mutes HA output and restores listening on stop", async (t) => {
  const { session, video } = harness(t); const pending = await begin(session);
  await ack(session, pending); assert.equal(pending.capture.mutedAtEnable, true);
  video.muted = false; video.dispatchEvent(new Event("volumechange")); assert.equal(video.muted, true);
  await session._disableMicrophone(); assert.equal(video.muted, false); assert.equal(pending.capture.closed, true);
});
test("stale acknowledgements cannot revoke a new microphone epoch", async (t) => {
  const { session } = harness(t); const old = await begin(session); await ack(session, old);
  await session._disableMicrophone(); const current = await begin(session);
  await session._event({ type: "microphone", enabled: false, request_id: old.request }, session.generation);
  assert.equal(session.capture, current.capture); await ack(session, current);
  await session.stop();
});
test("microphone failure releases capture but never replaces or stops HA video", async (t) => {
  const { session, video, host, states } = harness(t); const pending = await begin(session); await ack(session, pending);
  await session._fail(session.generation);
  assert.equal(host.children[0], video); assert.equal(video.muted, false);
  assert.equal(pending.capture.closed, true); assert.equal(states.at(-1).microphoneSupported, false);
  assert.equal(states.at(-1).phase, undefined);
});
test("late capture errors cannot affect a replacement or newer session", async (t) => {
  const { session, controls } = harness(t); const old = await begin(session); await ack(session, old);
  await session._disableMicrophone(); const current = await begin(session); await ack(session, current);
  const count = controls.length;
  old.capture.onError(new Error("late")); await new Promise(setImmediate);
  assert.equal(session.capture, current.capture); assert.equal(controls.length, count);
  session.generation++; current.capture.onError(new Error("old generation"));
  await new Promise(setImmediate); assert.equal(controls.length, count); await session.stop();
});
test("unsupported offer revokes capture immediately without restarting video", async (t) => {
  const { session, host, video } = harness(t); const pending = await begin(session); await ack(session, pending);
  await session._event({ type: "audio_offer", connected: false, supported: false }, session.generation);
  assert.equal(session.capture, null); assert.equal(host.children[0], video); await session.stop();
});

test("old pending enable cleanup cannot disable a replacement capture", async (t) => {
  const { session } = harness(t); const old = await begin(session);
  const disabling = session._disableMicrophone();
  const starting = begin(session);
  await disabling; await old.completion;
  const current = await starting;
  assert.equal(session.capture, current.capture); assert.equal(session.pending, true);
  await ack(session, current); await session.stop();
});

test("player replacement during acknowledgement cannot start unmuted capture", async (t) => {
  const { session, host } = harness(t); const pending = await begin(session);
  host.children = [Object.assign(new EventTarget(), { localName: "video", muted: false, children: [] })];
  await session._event({ type: "microphone", enabled: true, request_id: pending.request }, session.generation);
  await pending.completion;
  assert.equal(pending.capture.active, false); assert.equal(session.capture, null);
  assert.equal(session.microphone, false); await session.stop();
});

test("each PCM frame rejects a hidden page or replaced player before network send", async (t) => {
  const previousDocument = globalThis.document;
  globalThis.document = { hidden: false };
  try {
    const { session, host, controls } = harness(t); const pending = await begin(session);
    await ack(session, pending);
    await pending.capture.onFrame("synthetic"); const count = controls.length;
    document.hidden = true;
    assert.throws(() => pending.capture.onFrame("synthetic"));
    document.hidden = false; host.children = [];
    assert.throws(() => pending.capture.onFrame("synthetic"));
    assert.equal(controls.length, count); await session.stop();
  } finally {
    if (previousDocument === undefined) delete globalThis.document;
    else globalThis.document = previousDocument;
  }
});
