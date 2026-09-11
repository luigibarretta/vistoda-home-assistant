import { copy, localizeCopy } from "./panel-copy.js";
const LABELS = {
  private: "privato all'app",
  addon_config: "configurazione pubblica dell'app",
  media: "media di Home Assistant",
  share: "share di Home Assistant",
  custom: "percorso personalizzato",
};

export function recordingStorageSummary(storage, context = "it") {
  if (!storage?.directory) return copy(context, "Percorso non esposto da questa versione del bridge.");
  const kind = LABELS[storage.kind] ? copy(context, LABELS[storage.kind]) : storage.kind;
  return copy(context, "Archivio: {p0} · {p1}", { p0: storage.directory, p1: kind });
}

export function recordingInfoContent(recording, storage, context = "it") {
  const content = document.createElement("div");
  content.className = "recording-info";
  const line = document.createElement("div");
  line.className = "path-line";
  const text = document.createElement("div");
  const label = document.createElement("strong");
  label.textContent = `${copy(context, "Percorso file")} `;
  const path = document.createElement("code");
  path.textContent = recording.storage_path || copy(context, "Non disponibile con questo bridge");
  text.append(label, path);
  const note = document.createElement("div");
  note.className = "hint";
  note.textContent = storage?.user_visible
    ? copy(context, "Percorso accessibile dallo storage Home Assistant selezionato.")
    : copy(context, "Storage privato dell'app. La destinazione si cambia nella configurazione di Vistoda Ring.");
  text.append(note);
  const button = document.createElement("button");
  button.className = "row-action path-copy";
  button.disabled = !recording.storage_path;
  button.innerHTML = '<ha-icon icon="mdi:content-copy"></ha-icon><span data-copy="Copia"></span>';
  localizeCopy(button, context);
  button.addEventListener("click", () => content.dispatchEvent(new CustomEvent("copy-path", {
    detail: { path: recording.storage_path },
  })));
  line.append(text, button);
  content.append(line);
  return content;
}

export function recordingInfoRow(recording, storage, context = "it") {
  const row = document.createElement("tr");
  row.className = "info-row";
  const cell = document.createElement("td");
  cell.colSpan = 4;
  cell.append(recordingInfoContent(recording, storage, context));
  row.append(cell);
  return row;
}

export async function copyRecordingPath(path) {
  if (!path || !navigator.clipboard?.writeText) return false;
  try {
    await navigator.clipboard.writeText(path);
    return true;
  } catch (_error) {
    return false;
  }
}
