import { copy } from "./panel-copy.js";

// Mirrors Blink Android 59.1 LocalStorageState: each non-active state opens a
// dedicated screen in the official app, so Vistoda shows the same diagnosis,
// wording and single next action.
const COMPATIBLE_STORAGE_URL = "https://support.blinkforhome.com/en_US/681665";
const TROUBLESHOOTING_URL = "https://support.blinkforhome.com/en_US/622488";
const USB_STATES = Object.freeze({
  format_required: { tone: "error", icon: "mdi:alert-circle-outline", badge: "Da formattare",
    title: "Formatta chiavetta USB", action: "format",
    text: "La chiavetta USB collegata deve essere formattata prima dell’uso. La formattazione cancella TUTTI i dati sul dispositivo e non può essere annullata." },
  incompatible: { tone: "error", icon: "mdi:close-octagon-outline", badge: "Non compatibile",
    title: "Chiavetta USB non compatibile",
    link: ["Scopri i supporti di archiviazione esterni compatibili", COMPATIBLE_STORAGE_URL],
    text: "La chiavetta USB collegata non è compatibile. Prova a inserire un altro dispositivo o apri il link qui sotto per scoprire quali supporti esterni puoi usare con il Sync Module." },
  memory_full: { tone: "warning", icon: "mdi:database-alert-outline", badge: "Piena",
    title: "Chiavetta USB piena", action: "eject",
    warning: "Finché il supporto è pieno potresti avere problemi con la registrazione delle clip e con la live.",
    text: "Il supporto di archiviazione locale collegato è troppo pieno per essere usato. Libera spazio per usarlo o usa un’altra chiavetta USB." },
  unavailable: { tone: "warning", icon: "mdi:usb-port", badge: "Assente",
    title: "Inserisci chiavetta USB",
    link: ["Risoluzione dei problemi dell’archiviazione locale", TROUBLESHOOTING_URL],
    text: "Il Sync Module può salvare le clip su un supporto di archiviazione locale compatibile. Inserisci una chiavetta USB nel Sync Module per iniziare." },
  unmounted: { tone: "info", icon: "mdi:eject-outline", badge: "Scollegata",
    title: "Chiavetta USB scollegata", action: "mount",
    text: "La chiavetta USB può essere rimossa in sicurezza dal Sync Module." },
});
// Banners of the native ACTIVE screen (LocalStorageMessage).
const ACTIVE_MESSAGES = Object.freeze({
  backing_up: { tone: "info", icon: "mdi:backup-restore", badge: "Backup in corso",
    title: "Backup in corso", text: "Ricontrolla tra qualche minuto." },
  almost_full: { tone: "error", icon: "mdi:database-alert-outline", badge: "Quasi piena",
    title: "L’archiviazione locale è quasi piena",
    text: "Per liberare spazio elimina delle clip o formatta il supporto di archiviazione locale." },
});
const READABLE_STATES = new Set(["active", "memory_full"]);
const BACKUP_FAILURES = Object.freeze({
  no_usb: "La chiavetta USB non era presente", usb_removed: "La chiavetta USB non era presente",
  usb_ejected: "La chiavetta USB era stata espulsa", memory_full: "La chiavetta USB era piena",
  sm_offline: "Il Sync Module era offline",
});
export const ACTION_LABELS = Object.freeze({ format: "Formatta chiavetta USB",
  eject: "Espelli chiavetta USB in sicurezza", mount: "Collega chiavetta USB" });
const ACTION_ICONS = Object.freeze({ format: "mdi:format-page-break", eject: "mdi:eject-outline", mount: "mdi:usb" });
// Capability flags computed by the engine from fresh provider status.
const ACTION_CAPABILITIES = Object.freeze({ format: "can_format_usb", eject: "can_eject_usb", mount: "can_mount_usb" });

export function usbState(storage) { return String(storage?.status?.usb_state || "").trim().toLowerCase(); }

/** Native state after its own fallbacks: unknown → incompatible, full incompatible → full. */
export function nativeUsbState(storage) {
  const state = usbState(storage);
  if (!state) return "";
  if (state === "active" || USB_STATES[state] && state !== "incompatible") return state;
  return storage?.status?.usb_storage_full ? "memory_full" : "incompatible";
}

/** Returns the authored notice for the provider state, or null when nothing is wrong. */
export function usbNotice(storage) {
  const state = nativeUsbState(storage);
  if (state !== "active") return USB_STATES[state] || null;
  if (storage.status?.backup_in_progress) return ACTIVE_MESSAGES.backing_up;
  return Number(storage.status?.storage_warning) >= 3 ? ACTIVE_MESSAGES.almost_full : null;
}

/** True when Blink reports a state whose index and usage are not meaningful. */
export function usbBlocked(storage) {
  const state = nativeUsbState(storage);
  return Boolean(state) && !READABLE_STATES.has(state);
}

export function backupFailure(status = {}) {
  const result = String(status.last_backup_result || "").toLowerCase();
  if (!status.last_backup_completed || !result || result === "success") return null;
  return BACKUP_FAILURES[result] || "";
}

export const blinkStorageState = {
  _usbNotice(storage) {
    const notice = usbNotice(storage); if (!notice) return null;
    // No live region: the module re-renders on every HA state push and would
    // repeat the announcement; the notice sits first in the module reading order.
    const node = document.createElement("section"); node.className = `usb-notice ${notice.tone}`;
    const glyph = document.createElement("ha-icon"); glyph.setAttribute("icon", notice.icon);
    const text = document.createElement("div"); const title = document.createElement("strong");
    title.textContent = copy(this, notice.title);
    const body = document.createElement("p"); body.textContent = copy(this, notice.text);
    text.append(title, body);
    if (notice.warning) {
      const warning = document.createElement("p"); warning.className = "usb-warning";
      warning.textContent = `${copy(this, "Attenzione")}: ${copy(this, notice.warning)}`; text.append(warning);
    }
    if (notice.link) text.append(this._usbLink(...notice.link));
    if (notice.action) text.append(this._usbAction(storage, notice.action));
    node.append(glyph, text); return node;
  },
  _usbLink(label, href) {
    const link = document.createElement("a"); link.className = "usb-notice-link"; link.href = href;
    link.target = "_blank"; link.rel = "noopener noreferrer"; link.textContent = copy(this, label);
    return link;
  },
  _usbAction(storage, action) {
    if (!storage.status?.[ACTION_CAPABILITIES[action]]) {
      const note = document.createElement("small");
      note.textContent = copy(this, "Questa operazione non è disponibile da Vistoda per questo supporto: usa l’app Blink.");
      return note;
    }
    const run = action === "format" ? () => this._openFormat(storage) : () => this._storageCommand(storage, action);
    const button = this._button(ACTION_ICONS[action], copy(this, ACTION_LABELS[action]), run);
    button.className = `usb-notice-action${action === "format" ? " danger" : ""}`; return button;
  },
  _ejectAction(storage) {
    if (!storage.status?.can_eject_usb) {
      return this._moduleAction("mdi:eject-outline", copy(this, "Espelli in sicurezza"),
        copy(this, "Disponibile solo con una chiavetta USB collegata e leggibile."));
    }
    const button = this._icon("mdi:eject-outline", copy(this, "Espelli in sicurezza"),
      () => this._storageCommand(storage, "eject"));
    button.removeAttribute("title"); return button;
  },
  _backupFacts(storage) {
    const status = storage.status || {};
    if (!status.last_backup_completed) return [];
    const when = this._date(status.last_backup_completed); const reason = backupFailure(status);
    if (reason === null) return [this._fact("mdi:cloud-check-outline", copy(this, "Ultimo backup Blink"), when)];
    const fact = reason
      ? this._fact("mdi:cloud-alert-outline", copy(this, "Backup non riuscito: {p0}", { p0: when }),
        `${copy(this, "Backup non riuscito")}: ${copy(this, reason)}`)
      : this._fact("mdi:cloud-alert-outline", copy(this, "Backup non riuscito"), when);
    fact.classList.add("backup-failed"); return [fact];
  },
  _usbSummary(storage, count) {
    const notice = usbNotice(storage); if (!notice) return count;
    const wrap = document.createElement("span"); wrap.className = "usb-summary";
    const badge = document.createElement("span"); badge.className = `usb-badge ${notice.tone}`;
    badge.textContent = copy(this, notice.badge); wrap.append(badge, count); return wrap;
  },
};
