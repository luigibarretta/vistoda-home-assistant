// UI copy belongs here. Device names, vendor values and errors are never translated.
export const PANEL_MESSAGES = {
  en: {
    eventLive: "Live video",
    overview: "Overview", controlCenter: "Your home, connected", reload: "Refresh",
    back: "Back to Home Assistant", refreshInventory: "Refresh devices and status",
    navigation: "Vistoda navigation", loading: "Loading devices…",
    inventoryError: "Unable to load devices. Check your Home Assistant connection and select Refresh to try again.",
    introTitle: "All your devices in one place",
    introBody: "Choose a brand to view cameras, answer the intercom and browse recordings.",
    ringDescription: "Intercom, two-way audio, entrances and call recordings",
    blinkDescription: "Cameras, live video, saved images, motion and cloud clips",
    ezvizDescription: "Cameras, saved images and live video on request",
    deviceCount: "{devices} devices · {cameras} cameras", notConfigured: "Not configured",
    ready: "Ready", unavailable: "Unavailable", absent: "Not connected",
    openProvider: "Open {provider}", configureProvider: "Set up {provider}",
    noCameras: "No {provider} cameras configured.", noIntercom: "No Ring intercom configured.",
    reconnect: "Manage connection", snapshotMissing: "Image time unavailable", snapshotAt: "Image captured {time}",
    history: "Event history", startCall: "Start conversation", microphone: "Enable microphone",
    ringSelect: "Choose an intercom", ringError: "Unable to load Ring. Select Retry to try again.", retry: "Retry",
    ezvizTitle: "EZVIZ cameras", ezvizIntro: "View the latest saved image. Live video and new images start when you request them.",
    savedImage: "Latest image saved in Home Assistant", blinkTitle: "Blink cameras",
    blinkIntro: "Saved images do not wake cameras. Refresh and live video start only when requested.",
    historyBack: "Back to intercom", historyRefresh: "Refresh event history", historyFilters: "History filters",
    entrances: "Entrances and intercoms", eventType: "Event type", allEvents: "All events",
    unlocks: "Unlocks", calls: "Calls", earlierEvents: "Load earlier events", historyLoading: "Loading event history…",
    historyCached: "Ring is unreachable. Showing events saved by Vistoda.",
    historyUnavailable: "Ring event history is temporarily unavailable. Use Refresh to try again.",
    noEvents: "No events match this filter.", today: "Today", yesterday: "Yesterday",
    eventUnlock: "Entrance unlocked", eventDing: "Intercom call", eventMotion: "Motion detected", eventActivity: "Ring activity",
    openLive: "Open live video", refreshSnapshot: "Take a new image", noSnapshot: "No saved image available",
    snapshotLoading: "Loading saved image…", cameraPrevious: "Previous camera", cameraNext: "Next camera",
    cameraSelect: "Choose a camera", battery: "Battery", temperature: "Temperature", recentClips: "Recent clips",
    connection: "Connection", onRequest: "On request", detailsSettings: "Details and settings",
    arm: "Arm", disarm: "Disarm", camera: "Camera", cameras: "Cameras", settings: "Settings",
    aboutButton: "Information, support and accessibility", aboutEyebrow: "Open source",
    aboutTitle: "About Vistoda", aboutSummary: "An independent project that brings supported cameras and intercoms into Home Assistant.",
    maintainedBy: "Maintained by the Vistoda author", githubProfile: "Luigi Barretta on GitHub",
    githubProfileNewWindow: "Open Luigi Barretta’s GitHub profile in a new window",
    supportKofi: "Support on Ko-fi", supportKofiNewWindow: "Open Ko-fi in a new window",
    independenceTitle: "Independent project", independenceShort: "Vistoda is not affiliated with, sponsored or endorsed by Amazon, Ring, Blink or EZVIZ. Product names and trademarks belong to their respective owners.",
    accessibilityPage: "Accessibility statement", accessibilityPageNewWindow: "Open the accessibility statement in a new window",
    fullDisclaimer: "Full disclaimer", fullDisclaimerNewWindow: "Open the full disclaimer in a new window", close: "Close",
  },
  it: {
    eventLive: "Video in diretta",
    overview: "Panoramica", controlCenter: "La tua casa connessa", reload: "Aggiorna",
    back: "Torna a Home Assistant", refreshInventory: "Aggiorna dispositivi e stato",
    navigation: "Navigazione Vistoda", loading: "Caricamento dispositivi…",
    inventoryError: "Impossibile caricare i dispositivi. Verifica la connessione a Home Assistant e premi Aggiorna per riprovare.",
    introTitle: "Tutti i dispositivi, una sola vista",
    introBody: "Scegli un marchio per vedere le telecamere, rispondere al citofono e consultare le registrazioni.",
    ringDescription: "Citofono, audio bidirezionale, ingressi e archivio chiamate",
    blinkDescription: "Telecamere, live, immagini salvate, movimento e clip cloud",
    ezvizDescription: "Telecamere, immagini salvate e live su richiesta",
    deviceCount: "{devices} dispositivi · {cameras} telecamere", notConfigured: "Non configurato",
    ready: "Operativo", unavailable: "Non disponibile", absent: "Non collegato",
    openProvider: "Apri {provider}", configureProvider: "Configura {provider}",
    noCameras: "Nessuna telecamera {provider} configurata.", noIntercom: "Nessun citofono Ring configurato.",
    reconnect: "Gestisci collegamento", snapshotMissing: "Ora snapshot non disponibile", snapshotAt: "Snapshot del {time}",
    history: "Cronologia eventi", startCall: "Avvia comunicazione", microphone: "Attiva microfono",
    ringSelect: "Scegli un citofono", ringError: "Impossibile caricare Ring. Premi Riprova per riprovare.", retry: "Riprova",
    ezvizTitle: "Telecamere EZVIZ", ezvizIntro: "Consulta l’ultima immagine salvata. Live e nuove immagini partono quando li richiedi.",
    savedImage: "Ultima immagine salvata in Home Assistant", blinkTitle: "Telecamere Blink",
    blinkIntro: "Gli snapshot esistenti non risvegliano le camere. Aggiornamento e live partono soltanto su richiesta.",
    historyBack: "Torna al citofono", historyRefresh: "Aggiorna cronologia", historyFilters: "Filtri cronologia",
    entrances: "Accessi e citofoni", eventType: "Tipo evento", allEvents: "Tutti gli eventi",
    unlocks: "Aperture", calls: "Chiamate", earlierEvents: "Carica eventi precedenti", historyLoading: "Caricamento cronologia…",
    historyCached: "Ring cloud non raggiungibile: sono mostrati gli eventi salvati da Vistoda.",
    historyUnavailable: "Cronologia Ring temporaneamente non disponibile. Premi Aggiorna per riprovare.",
    noEvents: "Nessun evento per questo filtro.", today: "Oggi", yesterday: "Ieri",
    eventUnlock: "Ingresso aperto", eventDing: "Chiamata al citofono", eventMotion: "Movimento rilevato", eventActivity: "Attività Ring",
    openLive: "Apri live", refreshSnapshot: "Aggiorna snapshot", noSnapshot: "Snapshot non disponibile",
    snapshotLoading: "Caricamento snapshot…", cameraPrevious: "Telecamera precedente", cameraNext: "Telecamera successiva",
    cameraSelect: "Seleziona telecamera", battery: "Batteria", temperature: "Temperatura", recentClips: "Clip recenti",
    connection: "Connessione", onRequest: "Su richiesta", detailsSettings: "Dettagli e impostazioni",
    arm: "Arma", disarm: "Disarma", camera: "Telecamera", cameras: "Telecamere", settings: "Impostazioni",
    aboutButton: "Informazioni, supporto e accessibilità", aboutEyebrow: "Open source",
    aboutTitle: "Informazioni su Vistoda", aboutSummary: "Un progetto indipendente che riunisce in Home Assistant telecamere e citofoni supportati.",
    maintainedBy: "Progetto mantenuto dall’autore di Vistoda", githubProfile: "Luigi Barretta su GitHub",
    githubProfileNewWindow: "Apri il profilo GitHub di Luigi Barretta in una nuova finestra",
    supportKofi: "Sostieni su Ko-fi", supportKofiNewWindow: "Apri Ko-fi in una nuova finestra",
    independenceTitle: "Progetto indipendente", independenceShort: "Vistoda non è affiliato, sponsorizzato o approvato da Amazon, Ring, Blink o EZVIZ. Nomi e marchi appartengono ai rispettivi titolari.",
    accessibilityPage: "Dichiarazione di accessibilità", accessibilityPageNewWindow: "Apri la dichiarazione di accessibilità in una nuova finestra",
    fullDisclaimer: "Avvertenza completa", fullDisclaimerNewWindow: "Apri l’avvertenza completa in una nuova finestra", close: "Chiudi",
  },
};

export function panelLanguage(hassOrLocale) {
  const language = typeof hassOrLocale === "string" ? hassOrLocale
    : hassOrLocale?.locale?.language || hassOrLocale?.language || "en";
  return language.toLowerCase().split(/[-_]/)[0] === "it" ? "it" : "en";
}

export function localize(hassOrLocale, key, values = {}) {
  const message = PANEL_MESSAGES[panelLanguage(hassOrLocale)][key] || PANEL_MESSAGES.en[key];
  if (!message) throw new Error(`Unknown Vistoda message: ${key}`);
  return message.replace(/\{(\w+)\}/g, (_, name) => String(values[name] ?? `{${name}}`));
}

// Explicit markers prevent accidental translation of device names and user content.
export function localizeElements(root, hass, values = {}) {
  root.host?.setAttribute("lang", panelLanguage(hass));
  root.querySelectorAll("[data-i18n]").forEach((element) => {
    element.textContent = localize(hass, element.dataset.i18n, values);
  });
  for (const attribute of ["aria-label", "title"]) {
    root.querySelectorAll(`[data-i18n-${attribute}]`).forEach((element) => {
      element.setAttribute(attribute, localize(hass, element.getAttribute(`data-i18n-${attribute}`), values));
    });
  }
}
