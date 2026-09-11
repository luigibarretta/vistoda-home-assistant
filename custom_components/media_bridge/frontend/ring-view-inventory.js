import { chooseRingEntry, storedRingEntry } from "./ring-entry-selection.js";
import { localize } from "./panel-localize.js";

export async function loadRingEntry(view) {
  view.$("connection-state").hidden = false;
  view.$("connection-message").textContent = localize(view._hass, "loading");
  view.$("retry").disabled = true;
  view.$("ring-main").hidden = true;
  try {
    const result = await view._hass.callWS({ type: "media_bridge/ring/info" });
    view._entries = result.entries || [];
    view._entry = chooseRingEntry(view._entries, view._requestedEntryId, storedRingEntry(view._storage));
    if (view._requestedEntryId && view._entry?.entry_id !== view._requestedEntryId) {
      view._answerMode = false;
    }
    view._available = Boolean(view._entry?.available);
    view.$("connection-state").hidden = Boolean(view._entry);
    view.$("ring-main").hidden = !view._entry;
    if (!view._entry) view.$("connection-message").textContent = localize(view._hass, "noIntercom");
    view._renderEntrySelector();
    view._renderAvailability();
    if (view._entry) view._configureEntry();
    view._renderState(view._entry ? { phase: "idle" } : {
      phase: "error", message: localize(view._hass, "noIntercom"),
    });
  } catch (_error) {
    view._available = false;
    view.$("connection-message").textContent = localize(view._hass, "ringError");
    view._renderState({ phase: "error", message: localize(view._hass, "ringError") });
  } finally {
    view.$("retry").disabled = false;
  }
}
