// Pure model of the SceneTrove microSD sync card (no browser dependencies).
// SceneTrove owns the schedule; the panel offers "off" plus these intervals.
export const SYNC_INTERVALS = [60, 180, 360, 720, 1440];
export const BATTERY_INTERVAL = 360;
export const MAINS_INTERVAL = 60;
// What SceneTrove accepts (ADR-0023); "off" may keep any of these.
export const MIN_INTERVAL = 15;
export const MAX_INTERVAL = 1440;

const INTERVAL_LABELS = {
  60: "Ogni ora", 180: "Ogni 3 ore", 360: "Ogni 6 ore", 720: "Ogni 12 ore", 1440: "Ogni 24 ore",
};
const RESULT_LABELS = {
  ok: "riuscita",
  camera_offline: "telecamera addormentata o offline",
  bridge_busy: "telecamera occupata",
  bridge_error: "app della telecamera non raggiungibile",
  unavailable: "non configurata in SceneTrove",
};
const ERROR_LABELS = {
  scenetrove_unauthorized: "SceneTrove ha rifiutato il token: serve un token di un amministratore con lo scope devices:sd-sync.",
  scenetrove_unknown_device: "SceneTrove non conosce questo dispositivo: controlla il dispositivo SceneTrove nelle opzioni.",
  scenetrove_live_source_required: "In SceneTrove questo dispositivo non ha la sorgente live: attivala prima di accendere la sincronizzazione.",
  scenetrove_unreachable: "SceneTrove non è raggiungibile.",
  scenetrove_unsupported_version: "Questa versione di SceneTrove non permette di cambiare la sincronizzazione da qui: aggiorna SceneTrove.",
  scenetrove_redirected: "SceneTrove ha risposto con un reindirizzamento: controlla l’indirizzo SceneTrove nelle opzioni.",
  unauthorized: "Solo un amministratore può cambiare la sincronizzazione.",
};

// A battery camera reports a level; each run wakes it, so it gets a longer default.
export function batteryPowered(entry) {
  return Number.isFinite(entry?.controls?.battery_percent);
}

export function recommendedInterval(entry) {
  return batteryPowered(entry) ? BATTERY_INTERVAL : MAINS_INTERVAL;
}

export function syncChoice(sync) {
  return sync?.enabled ? String(sync.interval_minutes) : "off";
}

// Choices for the select; a value set in SceneTrove outside the list stays visible.
export function syncChoices(sync) {
  const intervals = [...SYNC_INTERVALS];
  const current = Number(sync?.interval_minutes);
  if (sync?.enabled && Number.isInteger(current) && !intervals.includes(current)) intervals.push(current);
  return [
    { value: "off", label: "Disattivata", values: {} },
    ...intervals.sort((a, b) => a - b).map((minutes) => ({
      value: String(minutes),
      label: INTERVAL_LABELS[minutes] || "Ogni {p0} min",
      values: { p0: minutes },
    })),
  ];
}

// The request for a choice. "Off" sends the current interval back unchanged, even a
// custom one set in SceneTrove, so turning off never overwrites it.
export function scheduleFor(choice, sync, entry) {
  if (choice === "off") {
    const current = sync?.interval_minutes;
    const valid = Number.isInteger(current) && current >= MIN_INTERVAL && current <= MAX_INTERVAL;
    return { enabled: false, interval_minutes: valid ? current : recommendedInterval(entry) };
  }
  const minutes = Number(choice);
  return SYNC_INTERVALS.includes(minutes) ? { enabled: true, interval_minutes: minutes } : null;
}

export function resultLabel(result) {
  return RESULT_LABELS[result] || RESULT_LABELS.bridge_error;
}

export function errorLabel(code) {
  return ERROR_LABELS[code] || "SceneTrove non ha risposto correttamente: riprova più tardi.";
}

// What the card shows under the control: a hint when SceneTrove cannot run it.
export function syncNotice(sync) {
  if (sync?.enabled && sync.available === false) {
    return "SceneTrove non riesce a usare la sorgente live di questo dispositivo: controllala in SceneTrove.";
  }
  return "";
}
