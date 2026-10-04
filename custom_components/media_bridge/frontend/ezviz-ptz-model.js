// Pure PTZ helpers: map native EZVIZ PTZ buttons (by unique_id role) to a D-pad.
export const PTZ_DIRECTIONS = [
  { direction: "up", role: "ptz_up", icon: "mdi:chevron-up", label: "Muovi su" },
  { direction: "left", role: "ptz_left", icon: "mdi:chevron-left", label: "Muovi a sinistra" },
  { direction: "right", role: "ptz_right", icon: "mdi:chevron-right", label: "Muovi a destra" },
  { direction: "down", role: "ptz_down", icon: "mdi:chevron-down", label: "Muovi giù" },
];

// Only usable buttons count: a camera without PTZ entities gets no overlay at all.
export function ptzTargets(entities = [], states = {}) {
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
