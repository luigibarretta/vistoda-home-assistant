import assert from "node:assert/strict";
import test from "node:test";
import { ADVANCED_COPY } from "../custom_components/media_bridge/frontend/panel-copy.js";
import {
  SOURCE_CHANGED_COPY, cachedControlSource, controlSourceStale, liveControlSource, sourceSignature, writeAllowed,
} from "../custom_components/media_bridge/frontend/ezviz-control-source.js";

const SWITCH = "switch.vistoda_ezviz_front_door_delegate";
const entry = (source, extra = {}) => ({ entry_id: "e1", control_source: source, delegate_entity_id: SWITCH, ...extra });
const states = (state, last_changed = "t1") => (state === undefined ? {} : { [SWITCH]: { state, last_changed } });

test("the live source comes from the delegation switch state only", () => {
  assert.equal(liveControlSource(entry("vistoda"), states("on")), "native");
  assert.equal(liveControlSource(entry("native"), states("off")), "vistoda");
  // The switch is unavailable only while off (it stays available while delegated).
  assert.equal(liveControlSource(entry("native"), states("unavailable")), "vistoda");
  assert.equal(liveControlSource(entry("native"), states(undefined)), null, "reloading entry");
  assert.equal(liveControlSource(entry("native", { delegate_entity_id: undefined }), states("on")), null);
  assert.equal(cachedControlSource(entry(undefined)), "vistoda", "standalone is the default");
});

test("a snapshot is stale only when the live switch disagrees with it", () => {
  assert.equal(controlSourceStale(entry("native"), states("off")), true);
  assert.equal(controlSourceStale(entry("vistoda"), states("on")), true);
  assert.equal(controlSourceStale(entry("native"), states("on")), false);
  assert.equal(controlSourceStale(entry("vistoda"), states(undefined)), false);
});

test("writes to the official integration need the live switch to confirm delegation", () => {
  assert.equal(writeAllowed(entry("native"), states("on"), "native"), true);
  // Toggled to standalone while the panel still holds the delegated snapshot.
  assert.equal(writeAllowed(entry("native"), states("off"), "native"), false);
  assert.equal(writeAllowed(entry("native"), states("unavailable"), "native"), false);
  assert.equal(writeAllowed(entry("native"), states(undefined), "native"), false, "unverifiable");
  // A write prepared for one source is refused once the refreshed snapshot changed.
  assert.equal(writeAllowed(entry("vistoda"), states("off"), "native"), false);
  assert.equal(writeAllowed(null, states("on"), "native"), false);
});

test("Vistoda writes are refused only while the switch says delegated", () => {
  assert.equal(writeAllowed(entry("vistoda"), states("off"), "vistoda"), true);
  assert.equal(writeAllowed(entry("vistoda"), states(undefined), "vistoda"), true, "backend re-checks");
  assert.equal(writeAllowed(entry("vistoda"), states("on"), "vistoda"), false);
  assert.equal(writeAllowed(entry("native"), states("off"), "vistoda"), false);
});

test("the refresh signature changes on a flip or a re-created switch", () => {
  const entries = [entry("vistoda"), { entry_id: "e2" }];
  const base = sourceSignature(entries, states("off"));
  assert.equal(sourceSignature(entries, states("off")), base);
  assert.notEqual(sourceSignature(entries, states("on")), base);
  assert.notEqual(sourceSignature(entries, states("off", "t2")), base);
  assert.notEqual(sourceSignature(entries, states(undefined)), base);
  assert.equal(sourceSignature(undefined, undefined), "");
  assert.ok(Object.hasOwn(ADVANCED_COPY, SOURCE_CHANGED_COPY));
});
