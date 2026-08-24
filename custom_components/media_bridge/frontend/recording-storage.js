const LABELS = {
  private: "privato all'app",
  addon_config: "configurazione pubblica dell'app",
  media: "media di Home Assistant",
  share: "share di Home Assistant",
  custom: "percorso personalizzato",
};

export function recordingStorageSummary(storage) {
  if (!storage?.directory) return "Percorso non esposto da questa versione del bridge.";
  return `Archivio: ${storage.directory} · ${LABELS[storage.kind] || storage.kind}`;
}

export function recordingInfoRow(recording, storage) {
  const row = document.createElement("tr");
  row.className = "info-row";
  const cell = document.createElement("td");
  cell.colSpan = 4;
  const line = document.createElement("div");
  line.className = "path-line";
  const text = document.createElement("div");
  const label = document.createElement("strong");
  label.textContent = "Percorso file ";
  const path = document.createElement("code");
  path.textContent = recording.storage_path || "Non disponibile con questo bridge";
  text.append(label, path);
  const note = document.createElement("div");
  note.className = "hint";
  note.textContent = storage?.user_visible
    ? "Percorso accessibile dallo storage Home Assistant selezionato."
    : "Storage privato dell'app. La destinazione si cambia nella configurazione di Vistoda Ring.";
  text.append(note);
  const copy = document.createElement("button");
  copy.className = "row-action path-copy";
  copy.disabled = !recording.storage_path;
  copy.innerHTML = '<ha-icon icon="mdi:content-copy"></ha-icon><span>Copia</span>';
  copy.addEventListener("click", () => row.dispatchEvent(new CustomEvent("copy-path", {
    detail: { path: recording.storage_path },
  })));
  line.append(text, copy);
  cell.append(line);
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
