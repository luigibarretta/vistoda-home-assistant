import assert from "node:assert/strict";
import test from "node:test";

import {
  activityEnabled, allActivityDisabled, privacyContains, rectangleFromCells, setActivity,
} from "../custom_components/media_bridge/frontend/blink-zone-model.js";

test("native v1 activity masks map the 20 by 15 grid exactly", () => {
  let masks = Array(25).fill(4095);
  masks = setActivity(masks, 4, 3, false);
  assert.equal(activityEnabled(masks, 4, 3), false);
  assert.equal(activityEnabled(masks, 5, 3), true);
  assert.equal(allActivityDisabled(masks), false);
  assert.equal(allActivityDisabled(Array(25).fill(0)), true);
});

test("privacy rectangles normalize either drag direction and cover exact cells", () => {
  const zone = rectangleFromCells({ x: 6, y: 7 }, { x: 3, y: 4 });
  assert.deepEqual(zone, { x: 3, y: 4, w: 4, h: 4 });
  assert.equal(privacyContains([zone], 3, 4), true);
  assert.equal(privacyContains([zone], 7, 4), false);
});
