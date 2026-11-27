import assert from "node:assert/strict";
import test from "node:test";

import {
  normalizeFeatures, preferredTarget, recordTargets, tabEnabled, visibleTab,
} from "../custom_components/media_bridge/frontend/archive-features-model.js";

const TABS = ["usb", "local", "network"];

test("every archive is on unless the server says it is explicitly off", () => {
  assert.deepEqual(normalizeFeatures(undefined), { usb: true, local_ha: true, nfs: true });
  assert.deepEqual(normalizeFeatures({ usb: false, local_ha: "yes" }), { usb: false, local_ha: true, nfs: true });
  assert.equal(tabEnabled({ nfs: false }, "network"), false);
  assert.equal(tabEnabled({ nfs: false }, "local"), true);
});

test("the shown tab moves to the first active one when its archive is switched off", () => {
  assert.equal(visibleTab({}, TABS, "local"), "local");
  assert.equal(visibleTab({ local_ha: false }, TABS, "local"), "usb");
  assert.equal(visibleTab({ usb: false, local_ha: false }, TABS, "usb"), "network");
  assert.equal(visibleTab({ usb: false, local_ha: false, nfs: false }, TABS, "usb"), null);
});

test("REC offers only the destinations that are active, and none when both are off", () => {
  assert.deepEqual(recordTargets({}), { provider: true, ha: true, any: true });
  assert.deepEqual(recordTargets({ usb: false }), { provider: false, ha: true, any: true });
  assert.deepEqual(recordTargets({ usb: false, local_ha: false }), { provider: false, ha: false, any: false });
  assert.equal(recordTargets({ nfs: false }).any, true, "the network backup is not a REC destination");
});

test("the REC destination falls back to the one that is still active", () => {
  assert.equal(preferredTarget({}, "provider"), "provider");
  assert.equal(preferredTarget({ usb: false }, "provider"), "ha");
  assert.equal(preferredTarget({ local_ha: false }, "ha"), "provider");
  assert.equal(preferredTarget({ usb: false, local_ha: false }, "ha"), null);
});
