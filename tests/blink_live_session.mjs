import assert from "node:assert/strict";
import test from "node:test";

import { BlinkLiveSession } from "../custom_components/media_bridge/frontend/blink-live-session.js";
import { BlinkLegacyLiveSession } from "../custom_components/media_bridge/frontend/blink-legacy-live-session.js";

function harness() {
  const order = [];
  const states = [];
  let emit;
  const webRtc = {
    start: async () => { order.push("webrtc:start"); },
    stop: async () => { order.push("webrtc:stop"); },
  };
  const legacy = {
    start: async (entityId) => { order.push(`legacy:start:${entityId}`); },
    stop: () => { order.push("legacy:stop"); },
  };
  const session = new BlinkLiveSession({}, {}, {}, (state) => states.push(state), {
    webRtc: (handler) => { emit = handler; return webRtc; },
    legacy: () => legacy,
  });
  return { legacy, order, session, states, webRtc, emit: (value) => emit(value) };
}

test("official fallback stops Cayuga before starting Walnut", async () => {
  const item = harness();
  await item.session.start("kitchen", "camera.kitchen", "cayuga");
  item.emit({ phase: "fallback", reason: "blink_legacy_device" });
  await new Promise((resolve) => setTimeout(resolve, 0));

  assert.deepEqual(item.order, ["webrtc:start", "webrtc:stop", "legacy:start:camera.kitchen"]);
  assert.equal(item.session.mode, "legacy");
  assert.equal(item.states.at(-1).transport, "walnut");
});

test("ordinary WebRTC failure is fail-closed until manual compatible live", async () => {
  const item = harness();
  await item.session.start("kitchen", "camera.kitchen", "cayuga");
  item.emit({ phase: "error", providerCode: 2, message: "setup failed" });
  await new Promise((resolve) => setTimeout(resolve, 0));

  assert.deepEqual(item.order, ["webrtc:start"]);
  assert.equal(item.states.at(-1).legacyAvailable, true);
  await item.session.startLegacy();
  assert.deepEqual(item.order, ["webrtc:start", "webrtc:stop", "legacy:start:camera.kitchen"]);
});

test("automatic fallback is one-way per start", async () => {
  const item = harness();
  await item.session.start("kitchen", "camera.kitchen", "cayuga");
  item.emit({ phase: "fallback", reason: "no_ring_device_id" });
  item.emit({ phase: "fallback", reason: "blink_legacy_device" });
  await new Promise((resolve) => setTimeout(resolve, 0));

  assert.equal(item.order.filter((entry) => entry.startsWith("legacy:start")).length, 1);
});

test("official policy selects Walnut without constructing Cayuga", async () => {
  const item = harness();
  await item.session.start("kitchen", "camera.kitchen");

  assert.deepEqual(item.order, ["legacy:start:camera.kitchen"]);
  assert.equal(item.session.mode, "legacy");
  assert.equal(item.states.at(-1).transport, "walnut");
});

test("Walnut fallback mounts the Home Assistant live camera player", async () => {
  let config;
  const classes = [];
  const card = { classList: { add: (value) => classes.push(value) } };
  const host = {
    hidden: true,
    children: [],
    replaceChildren(...children) { this.children = children; },
  };
  globalThis.loadCardHelpers = async () => ({
    createCardElement: async (value) => { config = value; return card; },
  });
  try {
    const session = new BlinkLegacyLiveSession({ locale: "it" }, host);
    await session.start("camera.kitchen");
    assert.deepEqual(config, {
      type: "picture-entity", entity: "camera.kitchen", camera_view: "live",
      show_name: false, show_state: false,
      tap_action: { action: "none" }, hold_action: { action: "none" },
    });
    assert.deepEqual(classes, ["blink-legacy-card"]);
    assert.equal(host.hidden, false);
    assert.deepEqual(host.children, [card]);
    session.stop();
    assert.equal(host.hidden, true);
    assert.deepEqual(host.children, []);
  } finally {
    delete globalThis.loadCardHelpers;
  }
});
