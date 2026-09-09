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

export function booleanStateText(value) {
  return value === true ? "Attivata" : "Disattivata";
}

export function videoQualityOptions(options = [], current = "") {
  const available = new Set(options);
  if (current) available.add(current);
  const ordered = [
    ...QUALITY_ORDER.filter((value) => available.has(value)),
    ...Array.from(available).filter((value) => !QUALITY_ORDER.includes(value)),
  ];
  return ordered.map((value) => ({
    value,
    label: QUALITY_COPY[value]?.label || value,
    description: QUALITY_COPY[value]?.description || "Opzione supportata dalla telecamera.",
  }));
}
