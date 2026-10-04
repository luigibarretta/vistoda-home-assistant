// Separate camera reachability (native EZVIZ) from the Vistoda app/bridge health.
const KNOWN = new Set(["on", "off"]);

function scopeOf(hass, entity) {
  return hass?.states?.[entity?.entity_id]?.attributes?.connectivity_scope || "";
}

function stateOf(hass, entity) {
  const state = entity?.entity_id ? hass?.states?.[entity.entity_id]?.state : undefined;
  return KNOWN.has(state) ? state : "unknown";
}

export function ezvizConnectivity(hass, device) {
  const sensors = (device?.entities?.binary_sensor || [])
    .filter((item) => item.device_class === "connectivity");
  const camera = sensors.find((item) => scopeOf(hass, item) === "camera") || null;
  // Bridges from older releases do not expose a scope attribute yet.
  const bridge = sensors.find((item) => scopeOf(hass, item) === "bridge")
    || sensors.find((item) => item !== camera && !scopeOf(hass, item)) || null;
  return { camera: stateOf(hass, camera), bridge: stateOf(hass, bridge) };
}

export function connectionCopyKey(state) {
  if (state === "on") return "Connesso";
  return state === "off" ? "Disconnesso" : "Non rilevata";
}
