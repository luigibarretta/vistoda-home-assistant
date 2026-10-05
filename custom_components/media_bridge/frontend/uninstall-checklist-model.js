// Pure "before uninstalling the official app" checklist. No network calls:
// statuses are derived only from panel info and entity states already loaded.
import { encryptionView, storageView } from "./ezviz-media-model.js";
import { ringUnlockView } from "./ring-unlock-model.js";

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
    "Verifica che inserimento, impostazioni e connessione delle telecamere EZVIZ funzionino in Home Assistant (app Vistoda EZVIZ 0.10+ oppure integrazione EZVIZ nativa).",
    "Controlla lo stato della microSD prima di perdere l’accesso dall’app.",
  ],
};

const [BLINK_PROGRAMS] = CHECKLIST.blink;
const RING_UNLOCK = CHECKLIST.ring[1];
const [EZVIZ_CODE, EZVIZ_CORE, EZVIZ_SD] = CHECKLIST.ezviz;
const RANK = { todo: 0, ok: 1, warn: 2 };
// Several cameras or intercoms: the item shows the most urgent finding.
const worst = (items) => items.reduce((best, item) => (item && (!best || RANK[item.state] > RANK[best.state]) ? item : best), null);

// Vistoda Blink 0.23 "Programma: …" switches carry a program_id attribute.
export function blinkPrograms(states = {}) {
  return Object.entries(states || {})
    .filter(([entityId, state]) => entityId.startsWith("switch.") && state?.attributes?.program_id != null)
    .map(([entityId, state]) => ({ entityId, name: state.attributes.friendly_name || entityId, on: state.state === "on" }))
    .sort((a, b) => a.name.localeCompare(b.name));
}

function blinkStatus(states) {
  const programs = blinkPrograms(states);
  if (!programs.length) return {};
  const enabled = programs.filter((program) => program.on);
  return { [BLINK_PROGRAMS]: enabled.length
    ? { state: "warn", note: "Programmi ancora attivi: aprili per disattivarli.",
      links: enabled.map(({ entityId, name }) => ({ entityId, name })) }
    : { state: "ok", note: "Nessun programma attivo" } };
}

function ringStatus(entries, states) {
  const views = entries.map((entry) => ringUnlockView(states?.[entry.unlock_entity_id])).filter((view) => view?.mode);
  if (!views.length) return {};
  if (views.some((view) => view.ringToOpen)) {
    return { [RING_UNLOCK]: { state: "warn", note: "Ring-to-Open attivo: l’apertura remota può funzionare solo dopo una chiamata." } };
  }
  return views.every((view) => view.mode === "direct") ? { [RING_UNLOCK]: { state: "ok", note: "Apertura diretta" } } : {};
}

function encryptionItem(entry, states) {
  const view = encryptionView(entry.media?.encryption);
  if (view?.encrypted === false) return { state: "ok", note: "Crittografia video disattivata" };
  if (view?.encrypted === true) {
    if (view.keySource === "option") return { state: "ok", note: "Codice di verifica salvato nell’app Vistoda EZVIZ" };
    if (view.keySource === "none") return { state: "warn", note: "Crittografia attiva senza codice di verifica nell’app Vistoda EZVIZ" };
    if (view.keySource === "cloud") return { state: "warn", note: "Chiave letta dal cloud EZVIZ: annota comunque il codice di verifica" };
  }
  // Older apps: fall back to the native HA EZVIZ "encrypted" binary sensor.
  const native = (entry.native_entities || [])
    .some((entity) => entity.role === "encrypted" && states?.[entity.entity_id]?.state === "on");
  return native || view?.encrypted === true ? { state: "warn", note: "Crittografia video attiva" } : null;
}

const SD_NOTES = { no_card: "Nessuna microSD inserita", unformatted: "microSD da formattare", error: "Errore della microSD" };
function storageItem(entry, states) {
  const view = storageView(entry.media?.storage, states?.[entry.microsd_entity_id]);
  if (!view || view.status === "unknown") return null;
  return view.status === "ok" ? { state: "ok", note: "microSD funzionante" } : { state: "warn", note: SD_NOTES[view.status] };
}

// Vistoda EZVIZ 0.10+ controls use the app's own login; only older apps still
// need the native integration. Native metadata only resolves while the HA core
// EZVIZ coordinator owns the camera.
function controlsItem(entries) {
  const legacy = entries.filter((entry) => !entry.controls?.supported);
  if (!legacy.length) return { state: "ok", note: "Controlli tramite l’app Vistoda EZVIZ" };
  const unknown = legacy.every((entry) => !entry.controls);
  const linked = legacy.every((entry) => entry.device_name || entry.native_entities?.length);
  if (linked) return { state: "ok", note: "Integrazione nativa collegata" };
  return { state: "warn", note: unknown ? "Integrazione nativa non collegata"
    : "Aggiorna l’app Vistoda EZVIZ alla 0.10 o collega l’integrazione nativa" };
}

function ezvizStatus(entries, states) {
  const status = {};
  if (entries.length) status[EZVIZ_CORE] = controlsItem(entries);
  const code = worst(entries.map((entry) => encryptionItem(entry, states)));
  if (code) status[EZVIZ_CODE] = code;
  const card = worst(entries.map((entry) => storageItem(entry, states)));
  if (card) status[EZVIZ_SD] = card;
  return status;
}

const STATUS = {
  blink: (_entries, states) => blinkStatus(states),
  ring: ringStatus,
  ezviz: ezvizStatus,
};

// Returns one section per configured provider; each item is {text, state, note, links}.
export function checklistSections(info, states = {}) {
  return Object.entries(CHECKLIST).flatMap(([provider, items]) => {
    const providerInfo = info?.providers?.[provider];
    if (!providerInfo?.configured) return [];
    const computed = STATUS[provider](providerInfo.entries || [], states);
    return [{
      provider,
      items: items.map((text) => ({ text, state: computed[text]?.state || "todo", note: computed[text]?.note || "",
        links: computed[text]?.links || [] })),
    }];
  });
}
