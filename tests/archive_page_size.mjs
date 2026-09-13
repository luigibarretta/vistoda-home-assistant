import assert from "node:assert/strict";
import test from "node:test";
import { PAGE_SIZES, bindPageSize, renderPageSize } from "../custom_components/media_bridge/frontend/archive-page-size.js";
import { recordingPage } from "../custom_components/media_bridge/frontend/recording-table.js";

test("shared selector accepts only bounded supported sizes and disables mutations while busy", () => {
  let change;
  const select = { addEventListener: (_, handler) => { change = handler; }, localize: () => {} };
  const root = { getElementById: () => select };
  const calls = [];
  bindPageSize(root, (size) => calls.push(size));
  for (const value of [...PAGE_SIZES, 0, 101, 1000, NaN]) {
    select.value = value; select.disabled = false; change({ currentTarget: select });
  }
  assert.deepEqual(calls, [10, 25, 50, 100]);
  renderPageSize(root, 25, true);
  change({ currentTarget: select });
  assert.equal(select.value, 25); assert.equal(calls.length, 4);
});
test("Ring page sizes preserve exact bounded slices and clamp the final page", () => {
  const entries = Array.from({ length: 123 }, (_, index) => index);
  for (const size of PAGE_SIZES) {
    const first = recordingPage(entries, 1, size);
    assert.equal(first.items.length, size);
    const last = recordingPage(entries, 100, size);
    assert.equal(last.items.at(-1), 122);
    assert.ok(last.items.length <= size);
  }
});
