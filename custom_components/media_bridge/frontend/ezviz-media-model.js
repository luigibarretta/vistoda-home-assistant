// Pure view models for EZVIZ encryption, microSD status and the per-day SD
// record list (Vistoda EZVIZ 0.9+). Missing data always yields null/empty.
export const KEY_SOURCE_LABELS = {
  option: "Codice di verifica salvato nell’app Vistoda EZVIZ",
  cloud: "Chiave letta dal cloud EZVIZ",
  none: "Nessuna chiave disponibile",
};
export const STORAGE_LABELS = {
  ok: "Funzionante", no_card: "Nessuna scheda", unformatted: "Non formattata",
  error: "Errore", unknown: "Stato sconosciuto",
};
export const RECORD_LABELS = { event: "Evento", continuous: "Registrazione continua", other: "Altro" };
export const PROBLEM_STATUSES = ["no_card", "unformatted", "error"];
const DAY = /^\d{4}-\d{2}-\d{2}$/;

export function encryptionView(encryption) {
  if (!encryption || typeof encryption !== "object") return null;
  const encrypted = encryption.video_encrypted;
  const source = Object.hasOwn(KEY_SOURCE_LABELS, encryption.key_source) ? encryption.key_source : null;
  return {
    encrypted: typeof encrypted === "boolean" ? encrypted : null,
    label: encrypted === true ? "Attivata" : encrypted === false ? "Disattivata" : "Sconosciuta",
    source: encrypted === true && source ? KEY_SOURCE_LABELS[source] : "",
    keySource: source,
    // Live view cannot decrypt without the verification code option.
    warning: encrypted === true && source === "none",
  };
}

// The live sensor state wins over the panel's cached ten-minute poll.
export function storageView(storage, sensorState) {
  const live = sensorState && !["unknown", "unavailable"].includes(sensorState.state) ? sensorState.state : null;
  const status = live || (storage && typeof storage.status === "string" ? storage.status : null);
  if (!status) return null;
  const known = Object.hasOwn(STORAGE_LABELS, status) ? status : "unknown";
  const raw = live ? sensorState.attributes?.capacity_mb : storage?.capacity_mb;
  return {
    status: known,
    label: STORAGE_LABELS[known],
    capacityMb: Number.isInteger(raw) && raw > 0 ? raw : null,
    problem: PROBLEM_STATUSES.includes(known),
  };
}

export function capacityText(mb, locale = "it-IT") {
  if (!Number.isInteger(mb) || mb <= 0) return "";
  if (mb < 1024) return `${mb} MB`;
  return `${(mb / 1024).toLocaleString(locale, { maximumFractionDigits: 1 })} GB`;
}

export function isoDay(date) {
  const pad = (value) => String(value).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

// Today plus the six previous days, in the browser's calendar.
export function dayRange(now = new Date(), days = 7) {
  const first = new Date(now.getFullYear(), now.getMonth(), now.getDate() - (days - 1));
  return { min: isoDay(first), max: isoDay(now) };
}

export function clampDay(value, range) {
  return typeof value === "string" && DAY.test(value) && value >= range.min && value <= range.max ? value : range.max;
}

export function recordRows(records = [], locale = "it-IT") {
  const time = (seconds) => new Date(seconds * 1000).toLocaleTimeString(locale, { hour: "2-digit", minute: "2-digit" });
  return (Array.isArray(records) ? records : [])
    .filter((item) => Number.isInteger(item?.start) && Number.isInteger(item?.end) && item.end >= item.start)
    .slice(0, 500)
    .sort((a, b) => a.start - b.start)
    .map((item) => {
      const type = Object.hasOwn(RECORD_LABELS, item.type) ? item.type : "other";
      return { start: item.start, end: item.end, type, label: RECORD_LABELS[type],
        text: `${time(item.start)}–${time(item.end)}` };
    });
}
