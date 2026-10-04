import assert from "node:assert/strict";
import test from "node:test";
import { ADVANCED_COPY } from "../custom_components/media_bridge/frontend/panel-copy.js";
import { PTZ_DIRECTIONS, ptzServiceCall, ptzTargets } from "../custom_components/media_bridge/frontend/ezviz-ptz-model.js";

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
