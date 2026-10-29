// Pure EZVIZ alarm list helpers: no DOM, no network, deterministic for tests.
// Labels are Italian source keys looked up through the panel copy catalog.
export const ALARM_CATEGORIES = Object.freeze({
  motion: ["mdi:motion-sensor", "Movimento"],
  person: ["mdi:account-outline", "Persona"],
  vehicle: ["mdi:car-outline", "Veicolo"],
  doorbell: ["mdi:doorbell", "Campanello"],
  sound: ["mdi:volume-high", "Suono"],
  pet: ["mdi:paw", "Animale"],
  offline: ["mdi:lan-disconnect", "Offline"],
  tamper: ["mdi:shield-alert-outline", "Manomissione"],
  other: ["mdi:alarm-light-outline", "Altro allarme"],
});

const PICTURE_PATH = /^\/api\/media_bridge\/ezviz\/[A-Za-z0-9]{1,64}\/alarms\/[A-Za-z0-9_-]{1,128}\.jpg$/;

export function alarmCategory(value) {
  return Object.hasOwn(ALARM_CATEGORIES, value) ? value : "other";
}

// Only the integration's own relative picture route is ever signed or loaded.
export function alarmPicturePath(value) {
  return typeof value === "string" && PICTURE_PATH.test(value) ? value : null;
}

// Newest first, bounded, with every field normalized for safe rendering.
export function alarmRows(alarms, limit = 10) {
  if (!Array.isArray(alarms)) return [];
  return alarms
    .filter((item) => item && typeof item.alarm_id === "string" && item.alarm_id
      && Number.isSafeInteger(item.occurred_at) && item.occurred_at >= 0)
    .sort((left, right) => right.occurred_at - left.occurred_at)
    .slice(0, Math.max(0, limit))
    .map((item) => {
      const category = alarmCategory(item.category);
      const [icon, label] = ALARM_CATEGORIES[category];
      return {
        id: item.alarm_id,
        category,
        icon,
        label,
        title: typeof item.title === "string" ? item.title.slice(0, 160) : "",
        occurredAt: item.occurred_at,
        picture: alarmPicturePath(item.picture),
      };
    });
}

// Same-day alarms show only the time; older ones add the date.
export function alarmTimeText(seconds, language = "it-IT", now = Date.now(), timeZone = undefined) {
  if (!Number.isFinite(seconds)) return "";
  const date = new Date(seconds * 1000);
  const time = { hour: "2-digit", minute: "2-digit", timeZone };
  const day = new Intl.DateTimeFormat("en-CA", { dateStyle: "short", timeZone });
  const sameDay = day.format(date) === day.format(new Date(now));
  const options = sameDay ? time : { ...time, day: "numeric", month: "short" };
  return new Intl.DateTimeFormat(language, options).format(date);
}

export function alarmIsoTime(seconds) {
  return Number.isFinite(seconds) ? new Date(seconds * 1000).toISOString() : "";
}

// Alarms the card keeps while paging back (the app retains 200 per camera).
export const MAX_LOADED_ALARMS = 200;

// One page of the loaded rows. Until the app reports no older page
// (`complete`), the page count is unknown and the next page stays reachable;
// `needsMore` asks for the next older batch before this page can be filled.
export function alarmPage(rows, page, size, complete) {
  const loaded = Array.isArray(rows) ? rows : [];
  const pageSize = Math.max(1, Math.trunc(size) || 1);
  const totalPages = complete ? Math.max(1, Math.ceil(loaded.length / pageSize)) : null;
  const current = Math.max(1, Math.min(Math.trunc(page) || 1, totalPages ?? Infinity));
  const start = (current - 1) * pageSize;
  return {
    rows: loaded.slice(start, start + pageSize),
    page: current,
    totalPages,
    hasPrevious: current > 1,
    hasNext: loaded.length > start + pageSize || !complete,
    needsMore: !complete && loaded.length < start + pageSize,
  };
}
