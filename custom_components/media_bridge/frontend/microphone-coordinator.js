import { copy } from "./panel-copy.js";
const LOCK_NAME = "vistoda-active-microphone";
let fallbackLease = null;

export async function claimMicrophone(owner) {
  if (!navigator.locks?.request) {
    if (fallbackLease && fallbackLease !== owner) {
      throw new Error(copy(owner, "Il microfono è già usato da un’altra sessione Vistoda"));
    }
    fallbackLease = owner;
    return { release: () => { if (fallbackLease === owner) fallbackLease = null; } };
  }
  let releaseLock;
  let resolveReady;
  const ready = new Promise((resolve) => { resolveReady = resolve; });
  const held = new Promise((resolve) => { releaseLock = resolve; });
  navigator.locks.request(LOCK_NAME, { ifAvailable: true }, async (lock) => {
    resolveReady(Boolean(lock));
    if (lock) await held;
  }).catch(() => resolveReady(false));
  if (!await ready) throw new Error(copy(owner, "Il microfono è già usato da un’altra sessione Vistoda"));
  let released = false;
  return { release: () => { if (!released) { released = true; releaseLock(); } } };
}
