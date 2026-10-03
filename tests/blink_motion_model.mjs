import assert from "node:assert/strict";
import test from "node:test";
import { ADVANCED_COPY } from "../custom_components/media_bridge/frontend/panel-copy.js";
import { BATTERY_NOTICE, DELAY_NOTE, batteryCameras, draftChanged, draftValid, motionDraft,
  motionError, motionPayload, pollerStatus, toggleCamera }
  from "../custom_components/media_bridge/frontend/blink-motion-model.js";
import { recordingTrigger } from "../custom_components/media_bridge/frontend/provider-recording-model.js";

const cameras = [
  { alias: "front", name: "Ingresso", powered: true },
  { alias: "garden", name: "Giardino", powered: false },
  { alias: "garage", name: "Garage", powered: false },
];

test("poller states map to authored, translated status lines", () => {
  assert.deepEqual(pollerStatus({ state: "active", interval_seconds: 30 }),
    ["Controllo movimenti: attivo ogni {p0} s", { p0: 30 }]);
  const states = ["active", "idle", "backoff", "unauthorized", "disabled", "future", undefined];
  for (const state of states) {
    const [key] = pollerStatus(state ? { state } : null);
    assert.ok(Object.hasOwn(ADVANCED_COPY, key), `${state}: ${key}`);
  }
  assert.equal(pollerStatus({ state: "backoff" })[0], "Controllo movimenti: in pausa per limiti Blink");
  for (const text of [BATTERY_NOTICE, DELAY_NOTE, motionError({ code: "invalid" }),
    motionError({ code: "unauthorized" }), motionError({ code: "unavailable" }), motionError(null)]) {
    assert.ok(Object.hasOwn(ADVANCED_COPY, text), text);
  }
});

test("an empty camera list means all cameras and never an empty selection", () => {
  const all = motionDraft({ enabled: true, duration_seconds: 60, cameras: [] });
  assert.deepEqual(all, { enabled: true, all: true, cameras: [], duration_seconds: 60 });
  assert.deepEqual(motionPayload(all), { type: "blink_live_bridge/motion_recording/set",
    enabled: true, duration_seconds: 60, cameras: [] });
  const one = toggleCamera(all, cameras, "garden", false);
  assert.deepEqual(one.cameras, ["front", "garage"]);
  assert.equal(one.all, false);
  const none = toggleCamera(toggleCamera(one, cameras, "front", false), cameras, "garage", false);
  assert.equal(draftValid(none), false);
  assert.equal(draftValid(toggleCamera(none, cameras, "front", true)), true);
});

test("drafts sanitize the adapter payload and detect real changes only", () => {
  const draft = motionDraft({ enabled: "yes", duration_seconds: 45, cameras: ["garage", 7, "", "front"] });
  assert.deepEqual(draft, { enabled: false, all: false, cameras: ["garage", "front"], duration_seconds: 30 });
  assert.deepEqual(motionPayload(draft).cameras, ["front", "garage"]);
  const saved = { enabled: false, duration_seconds: 30, cameras: ["front", "garage"] };
  assert.equal(draftChanged(draft, saved), false);
  assert.equal(draftChanged({ ...draft, duration_seconds: 15 }, saved), true);
  assert.deepEqual(motionDraft(undefined), { enabled: false, all: true, cameras: [], duration_seconds: 30 });
});

test("the battery notice covers only selected battery cameras", () => {
  const all = motionDraft({ cameras: [] });
  assert.deepEqual(batteryCameras(all, cameras).map((camera) => camera.alias), ["garden", "garage"]);
  assert.deepEqual(batteryCameras(motionDraft({ cameras: ["front"] }), cameras), []);
  assert.deepEqual(batteryCameras(motionDraft({ cameras: ["garage"] }), cameras).map((c) => c.name), ["Garage"]);
  assert.deepEqual(batteryCameras(all), []);
});

test("only an explicit motion trigger marks a local recording", () => {
  assert.equal(recordingTrigger({ trigger: "motion" }), "motion");
  assert.equal(recordingTrigger({ trigger: "manual" }), "manual");
  assert.equal(recordingTrigger({}), "manual");
  assert.equal(recordingTrigger({ trigger: "<motion>" }), "manual");
  assert.ok(Object.hasOwn(ADVANCED_COPY, "Movimento"));
});
