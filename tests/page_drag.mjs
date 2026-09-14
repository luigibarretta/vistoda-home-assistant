import assert from "node:assert/strict";
import test from "node:test";
import { dragStart, dragMove, dragReset } from "../custom_components/media_bridge/frontend/page-drag.js";

test("shared drag recognizes the gesture without moving a resting snapshot", () => {
  const animations = [];
  const node = { style: { transform: "" }, animate: (...args) => animations.push(args) };
  const view = { $: () => node };
  const event = (x, y = 0) => ({ pointerId: 1, clientX: x, clientY: y, composedPath: () => [] });
  assert.equal(dragStart(view, event(100)), true);
  dragMove(view, event(40));
  assert.equal(node.style.transform, "");
  dragReset(view, 1);
  assert.equal(node.style.transform, "");
  assert.equal(animations.length, 0);
});

test("horizontal drag remains visually stable while preventing browser navigation", () => {
  const node = { style: { transform: "" }, classList: { add() {}, remove() {} } };
  const view = { $: () => node };
  let prevented = false;
  const event = (x) => ({ pointerId: 1, clientX: x, clientY: 0, cancelable: true,
    preventDefault: () => { prevented = true; }, composedPath: () => [] });
  dragStart(view, event(100)); dragMove(view, event(50));
  assert.equal(prevented, true);
  assert.equal(node.style.transform, "");
  dragReset(view); assert.equal(node.style.transform, "");
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

test("trusted pointer is captured at touch-down so the card keeps the gesture", () => {
  const captured = [], released = [];
  const node = { style: { transform: "" }, setPointerCapture: (id) => captured.push(id),
    hasPointerCapture: () => true, releasePointerCapture: (id) => released.push(id) };
  const view = { $: () => node };
  const start = { pointerId: 7, clientX: 100, clientY: 10, isTrusted: true,
    currentTarget: node, composedPath: () => [] };
  dragStart(view, start);
  assert.deepEqual(captured, [7]);
  dragMove(view, { ...start, clientX: 91 });
  assert.equal(view._swipeStart.horizontal, true);
  dragReset(view);
  assert.deepEqual(released, [7]);
});
