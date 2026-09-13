import assert from "node:assert/strict";
import test from "node:test";
import { dragStart, dragMove, dragReset } from "../custom_components/media_bridge/frontend/page-drag.js";

test("shared drag follows a finger, animates settling, and respects reduced motion", () => {
  const animations = [];
  const node = { style: { transform: "" }, animate: (...args) => animations.push(args) };
  const view = { $: () => node };
  const event = (x, y = 0) => ({ pointerId: 1, clientX: x, clientY: y, composedPath: () => [] });
  assert.equal(dragStart(view, event(100)), true);
  dragMove(view, event(40));
  assert.equal(node.style.transform, "translateX(-60px)");
  dragReset(view, 1);
  assert.equal(node.style.transform, "");
  assert.equal(animations[0][0][0].transform, "translateX(100%)");
  globalThis.matchMedia = () => ({ matches: true });
  try {
    dragStart(view, event(100)); dragMove(view, event(40)); dragReset(view, 1);
    assert.equal(node.style.transform, ""); assert.equal(animations.length, 1);
  } finally { delete globalThis.matchMedia; }
});

test("vertical scroll, controls and mismatched pointers never navigate", () => {
  const node = { style: { transform: "" } };
  const view = { $: () => node };
  const start = { pointerId: 1, clientX: 0, clientY: 0, composedPath: () => [] };
  assert.equal(dragStart(view, { ...start, composedPath: () => [{ localName: "button" }] }), false);
  assert.equal(dragStart(view, { ...start, composedPath: () => [{ id: "recording-section" }] }), false);
  dragStart(view, start);
  dragMove(view, { ...start, pointerId: 2, clientX: 60 });
  assert.equal(node.style.transform, "");
  dragMove(view, { ...start, clientY: 60 });
  assert.equal(view._swipeStart, null);
});
