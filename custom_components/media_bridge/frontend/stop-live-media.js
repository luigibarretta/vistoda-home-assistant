// Stop only media owned by this viewer, including players inside shadow roots.
// Removing a cached HA card alone need not synchronously stop audible tracks.
export function stopLiveMedia(root) {
  if (!root) return;
  if (["video", "audio"].includes(root.localName)) {
    root.muted = true;
    root.pause();
    for (const track of root.srcObject?.getTracks?.() || []) track.stop();
    root.srcObject = null;
    root.removeAttribute("src");
    root.load();
  }
  if (root.shadowRoot) stopLiveMedia(root.shadowRoot);
  for (const child of root.children || []) stopLiveMedia(child);
}
