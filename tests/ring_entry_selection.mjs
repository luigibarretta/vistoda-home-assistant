import assert from "node:assert/strict";
import test from "node:test";

import {
  RING_ENTRY_STORAGE_KEY,
  chooseRingEntry,
  saveRingEntry,
  storedRingEntry,
} from "../custom_components/media_bridge/frontend/ring-entry-selection.js";

const entries = [
  { entry_id: "offline", available: false },
  { entry_id: "hall", available: true },
  { entry_id: "garage", available: true },
];

test("requested Ring entry wins, then the remembered and first available entry", () => {
  assert.equal(chooseRingEntry(entries, "garage", "hall").entry_id, "garage");
  assert.equal(chooseRingEntry(entries, "missing", "hall").entry_id, "hall");
  assert.equal(chooseRingEntry(entries, "", "missing").entry_id, "hall");
  assert.equal(chooseRingEntry([{ entry_id: "only", available: false }]).entry_id, "only");
  assert.equal(chooseRingEntry([]), null);
});

test("Ring entry preference persists without failing in restricted storage", () => {
  const values = new Map();
  const storage = {
    getItem: (key) => values.get(key) || null,
    setItem: (key, value) => values.set(key, value),
  };
  saveRingEntry(storage, "hall");
  assert.equal(values.get(RING_ENTRY_STORAGE_KEY), "hall");
  assert.equal(storedRingEntry(storage), "hall");
  const blocked = { getItem: () => { throw new Error("blocked"); } };
  assert.equal(storedRingEntry(blocked), "");
});
