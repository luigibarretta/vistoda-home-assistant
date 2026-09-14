// Shared camera-page gesture recognition. The image stays centered while dragging.
const target = (view) => view.$("snapshot");
function discardPreview(view) {
  view._swipePreview?.remove?.(); view._swipePreview = null;
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
  card.style.transform = "";
}
export function dragReset(view, step = 0) {
  const start = view._swipeStart;
  const node = target(view);
  if (start?.capture?.hasPointerCapture?.(start.id)) start.capture.releasePointerCapture(start.id);
  view._swipeStart = null;
  if (!node) return;
  node.style.transform = ""; node.classList?.remove("drag-current-page");
  discardPreview(view);
}
