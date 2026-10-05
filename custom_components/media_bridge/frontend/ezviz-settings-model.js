// Pure grouping of native EZVIZ entities and Vistoda provider settings.
// Roles come from native unique_ids (server side), never from entity_id text.
const PTZ_ROLES = new Set(["ptz_up", "ptz_down", "ptz_left", "ptz_right"]);
// A native entity whose value Vistoda already shows as a provider setting.
const PROVIDER_DUPLICATES = { alarm_schedule: "alarm_schedule", detection_sensitivity: "detection_sensitivity" };

const has = (entity, ...parts) => parts.some((part) => entity.entity_id.includes(part));

export const GROUPS = [
  ["arming", "mdi:shield-home-outline", "Protezione e allarme", (e) => e.role === "alarm_schedule"],
  ["battery", "mdi:battery", "Batteria", (e) => e.device_class === "battery"],
  ["detection", "mdi:motion-sensor", "Rilevamento intelligente", (e) =>
    e.role === "detection_sensitivity" || has(e, "motion", "detection", "pir")],
  ["notifications", "mdi:bell-outline", "Notifiche", (e) => has(e, "notification", "alarm_notify")],
  ["audio", "mdi:microphone-outline", "Audio", (e) => has(e, "audio", "volume", "sound")],
  ["image", "mdi:image-outline", "Immagine", (e) => has(e, "image", "night", "infrared")],
  ["light", "mdi:lightbulb-outline", "Luci", (e) => e.domain === "light" || has(e, "light", "led")],
  ["privacy", "mdi:shield-outline", "Privacy", (e) => e.role === "encrypted" || has(e, "privacy", "sleep")],
  ["network", "mdi:wifi", "Rete", (e) => has(e, "wifi", "signal") || e.device_class === "signal_strength"],
  ["device", "mdi:information-outline", "Informazioni dispositivo", (e) =>
    e.domain === "update" || has(e, "firmware")],
];

export const PROVIDER_LABELS = {
  camera_defence: "Telecamera armata", alarm_schedule: "Programmazione allarme",
  detection_mode: "Modalità di rilevamento",
  battery_work_mode: "Modalità di lavoro", receive_device_message: "Ricevi messaggi dispositivo",
  answer_doorbell_call: "Rispondi alle chiamate citofono", offline_notification: "Notifica dispositivo offline",
  human_detection: "Rilevamento sagoma umana", wide_dynamic_range: "WDR",
  distortion_correction: "Correzione distorsione", logo_watermark: "Filigrana logo",
  detection_sensitivity: "Sensibilità di rilevamento", battery_level: "Livello batteria",
  infrared_light: "Luce infrarossa", status_light: "Spia di stato", privacy_mode: "Modalità privacy",
  sleep_mode: "Modalità riposo", firmware_version: "Versione firmware", firmware_update: "Aggiornamento firmware disponibile",
};

export const OPTION_LABELS = {
  power_saving: "Risparmio energetico", high_performance: "Prestazioni elevate",
  super_power_saving: "Super risparmio energetico", user_customization: "Personalizzazione utente",
  human_shape: "Sagoma umana", image_change: "Variazione immagine", pir: "Sensore PIR",
};

// Errors the settings/set command reports; anything else gets the generic message.
const SAVE_ERRORS = {
  conflict: "L’impostazione è cambiata su EZVIZ nel frattempo: controlla il valore attuale e riprova.",
  unconfirmed: "EZVIZ non ha confermato la modifica: controlla il valore attuale prima di riprovare.",
  reauth_required: "Accedi di nuovo a EZVIZ dall’integrazione Vistoda per modificare le impostazioni.",
};
export const saveErrorCopy = (code) => SAVE_ERRORS[code] || "Impossibile applicare le impostazioni EZVIZ.";

// Unknown app switches ("switch.<name>") get a readable, untranslated name.
export const providerLabel = (key) => PROVIDER_LABELS[key]
  || String(key).replace(/^switch\./, "").replace(/_/g, " ");

// Read-only values: booleans become Yes/No, numbers keep their unit.
export function infoText(setting) {
  if (typeof setting.value === "boolean") return setting.value ? "Sì" : "No";
  if (typeof setting.value === "number") return `${setting.value}${setting.unit || ""}`;
  return OPTION_LABELS[setting.value] || String(setting.value ?? "");
}

// A range input yields text; keep only integers inside the reported bounds.
export function numberValue(setting, raw) {
  const value = Number(raw);
  return Number.isInteger(value) && value >= setting.min && value <= setting.max ? value : null;
}

export const isActionable = (entity) => ["switch", "select", "number", "button", "light"].includes(entity.domain);

function hidden(entity, providerKeys) {
  if (PTZ_ROLES.has(entity.role)) return true; // PTZ lives in the live dialog.
  const duplicate = PROVIDER_DUPLICATES[entity.role];
  return Boolean(duplicate && providerKeys.has(duplicate));
}

export function settingsSections(entities = [], provider = []) {
  const providerKeys = new Set(provider.map((item) => item.key));
  const visible = entities.filter((entity) => !hidden(entity, providerKeys));
  const claimed = new Set();
  const sections = GROUPS.map(([key, icon, label, matches]) => {
    const rows = visible.filter((entity) => !claimed.has(entity.entity_id) && matches(entity));
    rows.forEach((entity) => claimed.add(entity.entity_id));
    return { key, icon, label, rows, provider: provider.filter((item) => item.group === key) };
  });
  const remainder = visible.filter((entity) => !claimed.has(entity.entity_id));
  const other = provider.filter((item) => item.group === "other");
  if (remainder.length || other.length) {
    sections.push({ key: "other", icon: "mdi:tune", label: "Altre impostazioni", rows: remainder, provider: other });
  }
  return sections;
}

// Each EZVIZ entry explicitly uses either the Vistoda EZVIZ app (standalone, the
// default) or the official Home Assistant EZVIZ integration (delegated).
const SOURCE_LABELS = { vistoda: "Vistoda", native: "Integrazione ufficiale" };
const SOURCE_HINTS = {
  app_outdated: "L’app Vistoda EZVIZ non offre ancora questi comandi: aggiornala alla 0.10 o attiva la delega all’integrazione EZVIZ ufficiale.",
  native_unavailable: "L’integrazione EZVIZ ufficiale non è disponibile: ripristinala o disattiva la delega per usare l’app Vistoda EZVIZ.",
};

export function controlSource(entry, errorCode) {
  const source = entry?.control_source === "native" ? "native" : "vistoda";
  return {
    source, label: SOURCE_LABELS[source], hint: SOURCE_HINTS[errorCode] || "",
    // Standalone never lists the official integration's entities as controls.
    entities: source === "native" ? entry?.native_entities || [] : [],
    switchEntityId: entry?.delegate_entity_id || null,
  };
}

// Explains the system arm/disarm card for the entry's control source.
export function systemScopeCopy(entry) {
  if (entry?.alarm_entity_id) return "Il comando Arma/Disarma si applica all’account EZVIZ associato.";
  if (entry?.control_source === "native") {
    return "Il pannello allarme dell’integrazione EZVIZ ufficiale non è disponibile: ripristinala o disattiva la delega.";
  }
  return entry?.controls?.supported === false
    ? "Aggiorna l’app Vistoda EZVIZ alla 0.10 o attiva la delega all’integrazione EZVIZ ufficiale per il controllo del sistema."
    : "Controllo del sistema non ancora disponibile dall’app Vistoda EZVIZ.";
}
