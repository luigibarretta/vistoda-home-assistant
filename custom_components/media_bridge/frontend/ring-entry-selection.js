export const RING_ENTRY_STORAGE_KEY = "vistoda-ring-selected-entry";

export function chooseRingEntry(entries, requestedId = "", storedId = "") {
  if (!Array.isArray(entries) || !entries.length) return null;
  const exact = (id) => entries.find((entry) => entry.entry_id === id);
  return exact(requestedId) || exact(storedId)
    || entries.find((entry) => entry.available) || entries[0];
}

export function storedRingEntry(storage) {
  try { return storage?.getItem(RING_ENTRY_STORAGE_KEY) || ""; } catch (_error) { return ""; }
}

export function saveRingEntry(storage, entryId) {
  try { storage?.setItem(RING_ENTRY_STORAGE_KEY, entryId); } catch (_error) { /* private mode */ }
}
