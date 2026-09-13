import { copy } from "./panel-copy.js";
import { entityState, firstEntity, pictureUrl, snapshotTimeText, wrappedIndex } from "./panel-helpers.js";

const put = (root, selector, value) => {
  const node = root.querySelector(selector); if (node) node.textContent = value;
};

export function hydrateBlinkDragPreview(view, clone, direction) {
  const cameras = view._cameras();
  const index = wrappedIndex(view._index, direction, cameras.length);
  const device = cameras[index], camera = firstEntity(device, "camera");
  const state = entityState(view._hass, camera), available = state?.state !== "unavailable";
  const image = clone.querySelector("img"), placeholder = clone.querySelector(".placeholder");
  const url = pictureUrl(view._hass, camera, view._nonce);
  if (image) { image.src = url || ""; image.alt = copy(view, "Snapshot {p0}", { p0: device.name });
    image.hidden = !url; }
  if (placeholder) placeholder.hidden = Boolean(url);
  put(clone, "h3", device.name);
  put(clone, ".media-title .muted", copy(view, "{p0} di {p1}", { p0: index + 1, p1: cameras.length }));
  put(clone, ".media-title .badge", available ? copy(view, "Disponibile") : copy(view, "Non disponibile"));
  const time = clone.querySelectorAll(".media-title .muted")[1];
  if (time) time.textContent = snapshotTimeText(state, view._hass?.locale?.language || "it-IT",
    view._snapshotTimes.get(camera?.entity_id));
  clone.querySelector(".media-title .badge")?.classList.toggle("off", !available);
}
