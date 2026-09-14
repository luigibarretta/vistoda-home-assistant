// Shared camera-page gesture feedback. Only the camera image follows the finger.
const target = (view) => view.$("snapshot");
const reduced = () => globalThis.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
function discardPreview(view) {
  view._swipePreview?.remove?.(); view._swipePreview = null;
}
function preview(view, direction) {
  if (view._swipePreview?.dataset?.direction === String(direction)) return view._swipePreview;
  discardPreview(view);
  const node = target(view), box = node?.getBoundingClientRect?.();
  if (!node || !box) return null;
  const clone = node.cloneNode(true);
  clone.querySelectorAll?.("[id]").forEach((item) => item.removeAttribute("id"));
  clone.querySelectorAll?.("video").forEach((item) => { item.pause?.(); item.removeAttribute("src"); });
  clone.classList.add("drag-adjacent-preview"); clone.dataset.direction = String(direction);
  clone.setAttribute("aria-hidden", "true"); clone.inert = true;
  Object.assign(clone.style, { top: `${box.top}px`, left: `${box.left}px`,
    width: `${box.width}px`, height: `${box.height}px` });
  view._hydrateDragPreview?.(clone, direction);
  node.parentNode?.insertBefore(clone, node); view._swipePreview = clone;
  return clone;
}
export function dragStart(view, event) {
  const path = event.composedPath?.() || [];
  if (event.button > 0 || path.some((node) =>
    ["button", "input", "select", "a", "video", "summary"].includes(node.localName) ||
      node.id === "recording-section" || node.localName === "vistoda-provider-recordings")) return false;
  target(view)?.getAnimations?.().forEach((animation) => animation.cancel());
  discardPreview(view);
  const capture = event.currentTarget || target(view);
  if (event.isTrusted) capture?.setPointerCapture?.(event.pointerId);
  view._swipeStart = { id: event.pointerId, x: event.clientX, y: event.clientY, capture };
  return true;
}
export function dragMove(view, event) {
  const start = view._swipeStart;
  if (!start || start.id !== event.pointerId) return;
  const dx = event.clientX - start.x, dy = event.clientY - start.y;
  if (!start.horizontal && Math.abs(dy) > 16 && Math.abs(dy) > Math.abs(dx) * 1.5) {
    dragReset(view); return;
  }
  if (!start.horizontal && Math.abs(dx) < 8) return;
  start.horizontal = true;
  const card = target(view);
  if (event.cancelable) event.preventDefault?.();
  if (!reduced()) {
    card.style.transform = `translateX(${dx}px)`; card.classList?.add("drag-current-page");
    const direction = dx < 0 ? 1 : -1, sibling = preview(view, direction);
    if (sibling) {
      const progress = Math.min(Math.abs(dx) / Math.max(card.clientWidth || 1, 1), 1);
      sibling.style.opacity = String(.18 + progress * .82);
      sibling.style.transform = `translateX(${direction * (100 - progress * 100)}%)`;
    }
  }
}
export function dragReset(view, step = 0) {
  const start = view._swipeStart;
  const node = target(view), previous = node?.style.transform || "none";
  if (start?.capture?.hasPointerCapture?.(start.id)) start.capture.releasePointerCapture(start.id);
  view._swipeStart = null;
  if (!node) return;
  node.style.transform = ""; node.classList?.remove("drag-current-page");
  discardPreview(view);
  if (reduced()) return;
  node.animate?.([
    { transform: step ? `translateX(${step > 0 ? 100 : -100}%)` : previous },
    { transform: "translateX(0)" },
  ], { duration: 220, easing: "cubic-bezier(.2,.8,.2,1)" });
}
