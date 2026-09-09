export const BLINK_SETTING_SECTIONS = [
  { key: "general", title: "Impostazioni generali", icon: "mdi:cog-outline",
    description: "Nome dispositivo, rete, firmware e temperatura." },
  { key: "motion", title: "Impostazioni movimento", icon: "mdi:motion-sensor",
    description: "Rilevamento, sensibilità, riattivazione e notifiche." },
  { key: "video", title: "Impostazioni video e foto", icon: "mdi:video-outline",
    description: "Qualità, durata clip, visione notturna e miniature." },
  { key: "audio", title: "Impostazioni audio", icon: "mdi:volume-high",
    description: "Volume dell’altoparlante e funzioni audio supportate." },
  { key: "privacy", title: "Impostazioni privacy", icon: "mdi:shield-lock-outline",
    description: "Registrazione, streaming audio, zone attività e privacy." },
];

export const BLINK_SETTING_META = {
  motion_detection: ["Rilevamento movimento", "Abilita gli eventi di movimento", "motion"],
  motion_sensitivity: ["Sensibilità", "Sensibilità del sensore di movimento", "motion"],
  retrigger_time: ["Tempo di riattivazione", "Pausa tra due eventi", "motion", "s"],
  early_notification: ["Notifica anticipata", "Avvisa all’inizio del movimento", "motion"],
  video_recording: ["Registrazione video", "Consenti alla camera di registrare", "privacy"],
  audio_streaming: ["Streaming audio", "Consenti le funzioni audio", "privacy"],
  clip_length: ["Durata clip", "Durata delle clip di movimento", "video", "s"],
  video_quality: ["Qualità video", "Regola la risoluzione video della telecamera", "video"],
  end_clip_early: ["Termina clip a movimento finito", "Ferma la clip quando cessa il movimento", "video"],
  night_vision: ["Visione notturna", "Modalità degli infrarossi", "video"],
  ir_intensity: ["Intensità IR", "Luminosità dei LED infrarossi", "video"],
  flip_video: ["Ruota video", "Ruota l’immagine quando la camera è capovolta", "video"],
  photo_capture: ["Acquisizione foto", "Una foto ogni ora; richiede un piano Blink idoneo", "video"],
  auto_thumbnail: ["Miniatura automatica", "Aggiorna la miniatura durante gli eventi", "video"],
  status_led: ["LED di stato", "Quando deve accendersi il LED della telecamera", "general"],
  speaker_volume: ["Volume altoparlante", "Livello audio dell’altoparlante", "audio"],
  sync_strength: ["Segnale Sync Module", "Ultima intensità radio rilevata", "general", "dBm"],
  camera_name: ["Nome telecamera", "Nome mostrato da Blink e Vistoda", "general"],
  temperature_alerts: ["Avvisi temperatura", "Stato configurato nell’account Blink", "general"],
  temperature_min: ["Temperatura minima", "Soglia inferiore", "general", "°F"],
  temperature_max: ["Temperatura massima", "Soglia superiore", "general", "°F"],
};

export const BLINK_OPTION_LABELS = {
  off: "Disattivata", on: "Attivata", auto: "Automatica",
  saver: "Risparmio", standard: "Standard", best: "Migliore",
  low: "Bassa", medium: "Media", high: "Alta", recording: "Durante la registrazione",
};

export function settingSection(field) {
  return (BLINK_SETTING_META[field.key] || [field.key, "", "general"])[2];
}
