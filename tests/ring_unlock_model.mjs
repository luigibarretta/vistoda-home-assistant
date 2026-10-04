import assert from "node:assert/strict";
import test from "node:test";
import { ADVANCED_COPY } from "../custom_components/media_bridge/frontend/panel-copy.js";
import { UNLOCK_LABELS, ringUnlockView } from "../custom_components/media_bridge/frontend/ring-unlock-model.js";

test("older engines and unavailable sensors hide the unlock settings", () => {
  assert.equal(ringUnlockView(undefined), null);
  assert.equal(ringUnlockView({ state: "unavailable", attributes: { duration_seconds: 5 } }), null);
  assert.equal(ringUnlockView({ state: "unknown", attributes: {} }), null);
});

test("unlock type, duration and the Ring-to-Open hint", () => {
  assert.deepEqual(ringUnlockView({ state: "direct", attributes: { duration_seconds: 5 } }),
    { mode: "direct", label: "Diretta", duration: 5, ringToOpen: false });
  assert.equal(ringUnlockView({ state: "ring_to_open", attributes: {} }).ringToOpen, true);
  const future = ringUnlockView({ state: "keypad", attributes: { ring_to_open_enabled: true, duration_seconds: -1 } });
  assert.deepEqual(future, { mode: "keypad", label: "keypad", duration: null, ringToOpen: true });
  assert.deepEqual(ringUnlockView({ state: "unknown", attributes: { duration_seconds: 3 } }),
    { mode: "", label: "", duration: 3, ringToOpen: false });
  for (const label of Object.values(UNLOCK_LABELS)) assert.ok(Object.hasOwn(ADVANCED_COPY, label), label);
});
