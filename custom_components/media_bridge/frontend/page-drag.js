// Shared camera-page gesture feedback. The whole camera card follows the finger.
const target = (view) => view.$("gallery") || view.$("snapshot");
const reduced = () => globalThis.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
export function dragStart(view, event) {
  const path = event.composedPath?.() || [];
  if (event.button > 0 || path.some((node) =>
    ["button", "input", "select", "a", "video", "summary"].includes(node.localName) ||
      node.id === "recording-section" || node.localName === "vistoda-provider-recordings")) return false;
  target(view)?.getAnimations?.().forEach((animation) => animation.cancel());
  view._swipeStart = { id: event.pointerId, x: event.clientX, y: event.clientY };
  return true;
}
export function dragMove(view, event) {
  const start = view._swipeStart;
  if (!start || start.id !== event.pointerId) return;
  const dx = event.clientX - start.x, dy = event.clientY - start.y;
  if (!start.horizontal && Math.abs(dy) > Math.max(12, Math.abs(dx))) {
    dragReset(view); return;
  }
  if (!start.horizontal && Math.abs(dx) < 12) return;
  start.horizontal = true;
  const card = target(view);
  if (event.isTrusted) card?.setPointerCapture?.(event.pointerId);
  if (!reduced()) target(view).style.transform = `translateX(${dx}px)`;
}
export function dragReset(view, step = 0) {
  const node = target(view), previous = node?.style.transform || "none";
  view._swipeStart = null;
  if (!node) return;
  node.style.transform = "";
  if (reduced()) return;
  node.animate?.([
    { transform: step ? `translateX(${step > 0 ? 100 : -100}%)` : previous },
    { transform: "translateX(0)" },
  ], { duration: 220, easing: "cubic-bezier(.2,.8,.2,1)" });
}
