// Pure "before uninstalling the official app" checklist. No network calls:
// statuses are derived only from panel info and entity states already loaded.
export const CHECKLIST = {
  blink: [
    "Disattiva i programmi di inserimento lato server (interruttori «Programma» di Vistoda Blink).",
    "Verifica che le notifiche di movimento arrivino in Home Assistant.",
    "Verifica gli avvisi della chiavetta USB (archivio pieno o non raggiungibile) in Home Assistant.",
  ],
  ring: [
    "Rimuovi il vecchio telefono dai dispositivi client autorizzati nel Centro di controllo Ring.",
    "Controlla il tipo di apertura (Ring-to-Open) e prova un’apertura da Home Assistant.",
    "Fai una chiamata di prova: deve arrivare in Home Assistant.",
  ],
  ezviz: [
    "Annota il codice di verifica del dispositivo (etichetta) e la password di crittografia video.",
    "Verifica che l’integrazione EZVIZ di Home Assistant sia connessa e che non ci sia la riparazione «L’integrazione EZVIZ di Home Assistant non è attiva».",
    "Controlla lo stato della microSD prima di perdere l’accesso dall’app.",
  ],
};

const EZVIZ_CORE = CHECKLIST.ezviz[1];
const EZVIZ_CODE = CHECKLIST.ezviz[0];

function ezvizStatus(entries, states) {
  const status = {};
  if (entries.length) {
    // Native metadata only resolves while the HA core EZVIZ coordinator owns the camera.
    const linked = entries.every((entry) => entry.device_name || entry.native_entities?.length);
    status[EZVIZ_CORE] = linked
      ? { state: "ok", note: "Integrazione nativa collegata" }
      : { state: "warn", note: "Integrazione nativa non collegata" };
  }
  const encrypted = entries.flatMap((entry) => entry.native_entities || [])
    .some((entity) => entity.role === "encrypted" && states?.[entity.entity_id]?.state === "on");
  if (encrypted) status[EZVIZ_CODE] = { state: "warn", note: "Crittografia video attiva" };
  return status;
}

// Returns one section per configured provider; each item is {text, state, note}.
export function checklistSections(info, states = {}) {
  return Object.entries(CHECKLIST).flatMap(([provider, items]) => {
    const providerInfo = info?.providers?.[provider];
    if (!providerInfo?.configured) return [];
    const computed = provider === "ezviz" ? ezvizStatus(providerInfo.entries || [], states) : {};
    return [{
      provider,
      items: items.map((text) => ({ text, state: computed[text]?.state || "todo", note: computed[text]?.note || "" })),
    }];
  });
}
