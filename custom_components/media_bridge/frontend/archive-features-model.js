// Which Blink archives the user keeps active: Blink USB, HA-local recordings, network backup.
export const FEATURES = ["usb", "local_ha", "nfs"];
// Archive tab (slot) name → the feature that switches it on.
export const TAB_FEATURE = { usb: "usb", local: "local_ha", network: "nfs" };

/** Everything is on unless the server says a feature is explicitly off. */
export function normalizeFeatures(raw) {
  return Object.fromEntries(FEATURES.map((name) => [name, raw?.[name] !== false]));
}

export function tabEnabled(features, tab) {
  return normalizeFeatures(features)[TAB_FEATURE[tab]];
}

/** The tab to show: the current one while it is active, else the first active one, else null. */
export function visibleTab(features, tabs, current) {
  const active = tabs.filter((tab) => tabEnabled(features, tab));
  return active.includes(current) ? current : active[0] ?? null;
}

/** Where a live recording can go: `provider` is Blink's archive, `ha` the Vistoda archive. */
export function recordTargets(features) {
  const { usb, local_ha: ha } = normalizeFeatures(features);
  return { provider: usb, ha, any: usb || ha };
}

/** The first destination of a live recording that is still active (`provider`, `ha` or null). */
export function preferredTarget(features, current) {
  const targets = recordTargets(features);
  if (targets[current]) return current;
  return targets.ha ? "ha" : targets.provider ? "provider" : null;
}
