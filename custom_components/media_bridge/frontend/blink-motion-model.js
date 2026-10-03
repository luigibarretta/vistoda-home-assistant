// Pure helpers for the adapter contract `blink_live_bridge/motion_recording/get|set`.
// In `settings.cameras` an empty list means every camera, so the draft keeps an
// explicit `all` flag: an empty individual selection is invalid, never "all".
export const MOTION_DURATIONS = Object.freeze([15, 30, 60]);
export const BATTERY_NOTICE = "Ogni registrazione accende la telecamera: sulle telecamere a batteria consuma batteria.";
export const DELAY_NOTE = "La registrazione parte dopo che Blink segnala il movimento (circa 30–60 secondi): riprende la scena successiva, non l'istante dell'evento.";
const POLLER = Object.freeze({
  idle: "Controllo movimenti: in attesa",
  backoff: "Controllo movimenti: in pausa per limiti Blink",
  unauthorized: "Controllo movimenti: accesso Blink da rinnovare",
  disabled: "Controllo movimenti: disattivato",
});
const ERRORS = Object.freeze({
  unauthorized: "Serve un account amministratore di Home Assistant.",
  invalid: "Impostazioni non valide: rileggi lo stato e riprova.",
});

/** Returns [authored copy, values] for the poller status line. */
export function pollerStatus(poller) {
  const seconds = Number(poller?.interval_seconds);
  if (poller?.state === "active") {
    return Number.isFinite(seconds) && seconds > 0
      ? ["Controllo movimenti: attivo ogni {p0} s", { p0: seconds }] : ["Controllo movimenti: attivo", {}];
  }
  return [POLLER[poller?.state] || "Controllo movimenti: stato non disponibile", {}];
}

export function motionDraft(settings = {}) {
  const duration = Number(settings?.duration_seconds);
  const cameras = Array.isArray(settings?.cameras)
    ? settings.cameras.filter((alias) => typeof alias === "string" && alias) : [];
  return { enabled: settings?.enabled === true, all: !cameras.length, cameras,
    duration_seconds: MOTION_DURATIONS.includes(duration) ? duration : 30 };
}

export function draftValid(draft) { return Boolean(draft) && (draft.all || draft.cameras.length > 0); }

export function motionPayload(draft) {
  return { type: "blink_live_bridge/motion_recording/set", enabled: draft.enabled === true,
    duration_seconds: draft.duration_seconds, cameras: draft.all ? [] : [...new Set(draft.cameras)].sort() };
}

export function draftChanged(draft, settings) {
  return JSON.stringify(motionPayload(draft)) !== JSON.stringify(motionPayload(motionDraft(settings)));
}

/** Cameras the draft covers; with no camera inventory the selection stays unknown. */
export function coveredCameras(draft, cameras = []) {
  return draft.all ? cameras : cameras.filter((camera) => draft.cameras.includes(camera.alias));
}

export function batteryCameras(draft, cameras = []) {
  return coveredCameras(draft, cameras).filter((camera) => camera.powered === false);
}

/** Selecting one camera out of "all" starts from every known camera. */
export function toggleCamera(draft, cameras, alias, selected) {
  const current = draft.all ? cameras.map((camera) => camera.alias) : draft.cameras;
  const next = selected ? [...new Set([...current, alias])] : current.filter((item) => item !== alias);
  return { ...draft, all: false, cameras: next };
}

export function motionError(error) {
  return ERRORS[error?.code] || "Registrazione al movimento non disponibile: riprova più tardi.";
}
