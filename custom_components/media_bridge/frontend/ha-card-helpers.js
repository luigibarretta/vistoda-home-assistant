// Custom panels may open before any Lovelace dashboard. Use HA's already
// registered route loader, never guess a hashed JS filename or navigate away.
let loading = null;

export async function loadHaCardHelpers(host) {
  if (typeof globalThis.loadCardHelpers === "function") return globalThis.loadCardHelpers();
  if (!loading) {
    loading = bootstrap(host).finally(() => { loading = null; });
  }
  await loading;
  if (typeof globalThis.loadCardHelpers !== "function") throw new Error("Home Assistant player unavailable");
  return globalThis.loadCardHelpers();
}

async function bootstrap(host) {
  let current = host; let route;
  while (current) {
    if (current.localName === "partial-panel-resolver") {
      route = Object.values(current.routerOptions?.routes || {}).find((candidate) =>
        candidate.tag === "ha-panel-lovelace" && typeof candidate.load === "function");
      if (route) break;
    }
    current = current.parentNode || current.host;
  }
  if (!route) throw new Error("Home Assistant player loader unavailable");
  let timeout;
  try {
    await Promise.race([route.load(), new Promise((_, reject) => {
      timeout = setTimeout(() => reject(new Error("Home Assistant player loading timed out")), 15000);
    })]);
  } finally { clearTimeout(timeout); }
}
