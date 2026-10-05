// Pure call-time resolution of an EZVIZ entry's control source. Panel info is
// a snapshot; the delegation switch state in hass.states is live, so writes are
// checked against it and a stale snapshot can never write to the wrong source.

// The switch is unavailable only while off: it stays available while delegated.
export function liveControlSource(entry, states) {
  const id = entry?.delegate_entity_id;
  const state = id ? states?.[id]?.state : undefined;
  if (state === "on") return "native";
  if (state === "off" || state === "unavailable") return "vistoda";
  return null; // No switch yet, or the entry is reloading.
}

export const cachedControlSource = (entry) => (entry?.control_source === "native" ? "native" : "vistoda");

// The snapshot disagrees with the live switch: panel info must be reloaded.
export function controlSourceStale(entry, states) {
  const live = liveControlSource(entry, states);
  return live !== null && live !== cachedControlSource(entry);
}

// target: the source the write was prepared for ("native" or "vistoda").
// Writes to the official integration need the live switch to confirm the
// delegation; Vistoda writes are refused while the switch says delegated (the
// backend re-checks the option on every Vistoda route and entity anyway).
export function writeAllowed(entry, states, target) {
  if (!entry || cachedControlSource(entry) !== target) return false;
  const live = liveControlSource(entry, states);
  return target === "native" ? live === "native" : live !== "native";
}

// Changes when any EZVIZ delegation switch flips or is re-created by a reload.
export function sourceSignature(entries = [], states = {}) {
  return entries.map((entry) => {
    const state = entry?.delegate_entity_id ? states?.[entry.delegate_entity_id] : undefined;
    return `${entry?.entry_id}:${state?.state ?? "-"}:${state?.last_changed ?? "-"}`;
  }).join("|");
}

export const SOURCE_CHANGED_COPY = "Origine dei comandi cambiata: aggiornamento del pannello in corso, riprova.";
