import assert from "node:assert/strict";
import test from "node:test";
import { ADVANCED_COPY } from "../custom_components/media_bridge/frontend/panel-copy.js";
import { PTZ_DIRECTIONS, entryPtzTargets, ptzRequest, ptzServiceCall, ptzTargets } from "../custom_components/media_bridge/frontend/ezviz-ptz-model.js";

const button = (direction) => ({ entity_id: `button.cam_${direction}`, domain: "button", role: `ptz_${direction}` });
const states = (ids, state = "unknown") => Object.fromEntries(ids.map((id) => [id, { state }]));

test("a PTZ camera gets a D-pad in reading order", () => {
  const entities = ["down", "up", "right", "left"].map(button);
  const targets = ptzTargets(entities, states(entities.map((item) => item.entity_id)));
  assert.deepEqual(targets.map((item) => item.direction), ["up", "left", "right", "down"]);
  assert.equal(targets[0].entityId, "button.cam_up");
});

test("cameras without usable PTZ buttons get no overlay", () => {
  assert.deepEqual(ptzTargets([], {}), []);
  assert.deepEqual(ptzTargets(undefined, undefined), []);
  const up = button("up");
  assert.deepEqual(ptzTargets([up], states([up.entity_id], "unavailable")), []);
  assert.deepEqual(ptzTargets([up], {}), [], "missing state means the entity is not loaded");
  const spoofed = { ...up, domain: "switch", entity_id: "switch.cam_up" };
  assert.deepEqual(ptzTargets([spoofed], states([spoofed.entity_id])), []);
});

test("each press maps to the native button service and labels are translated", () => {
  assert.deepEqual(ptzServiceCall({ entityId: "button.cam_up" }), ["button", "press", { entity_id: "button.cam_up" }]);
  for (const item of PTZ_DIRECTIONS) assert.ok(Object.hasOwn(ADVANCED_COPY, item.label), item.label);
  for (const label of ["Controllo PTZ", "Comando PTZ non riuscito"]) assert.ok(Object.hasOwn(ADVANCED_COPY, label));
});

test("app-reported PTZ drives every direction through the Vistoda EZVIZ app", () => {
  const targets = ptzTargets([], {}, "entry-1");
  assert.deepEqual(targets.map((item) => item.direction), ["up", "left", "right", "down"]);
  assert.deepEqual(ptzRequest(targets[0]), ["ws", { type: "media_bridge/ezviz/ptz", entry_id: "entry-1", direction: "up" }]);
  const native = ptzTargets([button("up")], states(["button.cam_up"]))[0];
  assert.deepEqual(ptzRequest(native), ["service", ["button", "press", { entity_id: "button.cam_up" }]]);
});

test("PTZ follows the entry's control source and never mixes the two", () => {
  const entities = ["up", "down", "left", "right"].map(button);
  const live = states(entities.map((item) => item.entity_id));
  const app = entryPtzTargets({ entry_id: "e1", controls: { ptz: true }, native_entities: entities }, live);
  assert.ok(app.length === 4 && app.every((item) => item.entryId === "e1" && !item.entityId));
  // Standalone with an older app (or no app PTZ): no silent native buttons.
  assert.deepEqual(entryPtzTargets({ entry_id: "e1", controls: { supported: false }, native_entities: entities }, live), []);
  const delegated = entryPtzTargets({ entry_id: "e1", control_source: "native", controls: { ptz: true },
    native_entities: entities }, live);
  assert.ok(delegated.length === 4 && delegated.every((item) => item.entityId && !item.entryId));
  assert.deepEqual(entryPtzTargets(null, live), []);
});
