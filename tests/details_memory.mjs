import assert from "node:assert/strict";
import test from "node:test";
import { rememberOpen } from "../custom_components/media_bridge/frontend/details-memory.js";

function details() {
  const listeners = {};
  return { open: false, addEventListener: (type, handler) => { listeners[type] = handler; }, fire: (type) => listeners[type]() };
}

test("sections stay as the user left them across rebuilds", () => {
  const closed = new Set();
  const first = details();
  rememberOpen(first, 7, closed);
  assert.equal(first.open, true, "open by default");
  first.open = false; first.fire("toggle");
  const rebuilt = details();
  rememberOpen(rebuilt, 7, closed);
  assert.equal(rebuilt.open, false, "a section the user closed stays closed");
  rebuilt.open = true; rebuilt.fire("toggle");
  assert.equal(closed.has("7"), false);
});
