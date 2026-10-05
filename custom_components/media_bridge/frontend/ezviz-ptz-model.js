// Pure PTZ helpers: map native EZVIZ PTZ buttons (by unique_id role) to a D-pad.
export const PTZ_DIRECTIONS = [
  { direction: "up", role: "ptz_up", icon: "mdi:chevron-up", label: "Muovi su" },
  { direction: "left", role: "ptz_left", icon: "mdi:chevron-left", label: "Muovi a sinistra" },
  { direction: "right", role: "ptz_right", icon: "mdi:chevron-right", label: "Muovi a destra" },
  { direction: "down", role: "ptz_down", icon: "mdi:chevron-down", label: "Muovi giù" },
];

// With Vistoda EZVIZ 0.10+ reporting PTZ, every direction goes through the app
// (appEntryId); otherwise only usable native buttons count, and a camera
// without PTZ entities gets no overlay at all.
export function ptzTargets(entities = [], states = {}, appEntryId = null) {
  if (appEntryId) return PTZ_DIRECTIONS.map((item) => ({ ...item, entryId: appEntryId }));
  return PTZ_DIRECTIONS.flatMap((item) => {
    const entity = entities.find((candidate) => candidate.role === item.role
      && candidate.domain === "button" && candidate.entity_id?.startsWith("button."));
    const state = entity ? states?.[entity.entity_id]?.state : undefined;
    return entity && state && state !== "unavailable" ? [{ ...item, entityId: entity.entity_id }] : [];
  });
}

// HA core EZVIZ 2026.8 has no ezviz.ptz service; each button press is one step.
export function ptzServiceCall(target) {
  return ["button", "press", { entity_id: target.entityId }];
}

// Returns ["ws", message] for the app route or ["service", args] for a native button.
export function ptzRequest(target) {
  if (target.entryId) return ["ws", { type: "media_bridge/ezviz/ptz", entry_id: target.entryId, direction: target.direction }];
  return ["service", ptzServiceCall(target)];
}
