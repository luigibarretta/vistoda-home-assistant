import { copy } from "./panel-copy.js";
const QUALITY_COPY = Object.freeze({
  best: Object.freeze({
    label: "Migliore",
    description: "Qualità video più elevata; riduce la durata della batteria. "
      + "Consigliata una velocità di upload di almeno 3 Mbps.",
  }),
  standard: Object.freeze({
    label: "Standard (consigliata)",
    description: "Qualità video HD. Consigliata una velocità di upload di almeno 2 Mbps.",
  }),
  saver: Object.freeze({
    label: "Risparmio",
    description: "Qualità video ridotta; prolunga la durata della batteria. "
      + "Consigliata una velocità di upload di almeno 500 Kbps.",
  }),
});

const QUALITY_ORDER = ["best", "standard", "saver"];

export function booleanStateText(value, context = "it") {
  return copy(context, value === true ? "Attivata" : "Disattivata");
}

export function temperatureValueText(value, hass) {
  if (!Number.isFinite(value)) return "—";
  const unit = hass?.config?.unit_system?.temperature === "°F" ? "°F" : "°C";
  const converted = unit === "°F" ? value : (value - 32) * 5 / 9;
  const locale = hass?.locale?.language || "it-IT";
  return `${converted.toLocaleString(locale, { maximumFractionDigits: 1 })} ${unit}`;
}

export function videoQualityOptions(options = [], current = "", context = "it") {
  const available = new Set(options);
  if (current) available.add(current);
  const ordered = [
    ...QUALITY_ORDER.filter((value) => available.has(value)),
    ...Array.from(available).filter((value) => !QUALITY_ORDER.includes(value)),
  ];
  return ordered.map((value) => ({
    value,
    label: QUALITY_COPY[value] ? copy(context, QUALITY_COPY[value].label) : value,
    description: copy(context, QUALITY_COPY[value]?.description || "Opzione supportata dalla telecamera."),
  }));
}
