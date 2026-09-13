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

test("horizontal drag reveals the adjacent card with progressive opacity", () => {
  const inserted = [], preview = { dataset: {}, style: {}, classList: { add() {} },
    setAttribute() {}, querySelectorAll: () => [], remove() { this.removed = true; } };
  const node = { clientWidth: 200, style: { transform: "" }, classList: { add() {}, remove() {} },
    cloneNode: () => preview, getBoundingClientRect: () => ({ top: 10, left: 20, width: 200, height: 300 }),
    parentNode: { insertBefore: (item) => inserted.push(item) } };
  const directions = [], view = { $: () => node,
    _hydrateDragPreview: (_clone, direction) => directions.push(direction) };
  let prevented = false;
  const event = (x) => ({ pointerId: 1, clientX: x, clientY: 0, cancelable: true,
    preventDefault: () => { prevented = true; }, composedPath: () => [] });
  dragStart(view, event(100)); dragMove(view, event(50));
  assert.equal(prevented, true);
  assert.equal(inserted.length, 1); assert.deepEqual(directions, [1]);
  assert.equal(preview.style.opacity, "0.385");
  assert.equal(preview.style.transform, "translateX(75%)");
  dragReset(view); assert.equal(preview.removed, true);
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
