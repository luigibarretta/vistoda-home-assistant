const STATUS = {
  pending: "In attesa", recording: "Registrazione in corso", ready: "Pronta", failed: "Non riuscita",
};

function button(icon, label, action, busy, className = "") {
  const node = document.createElement("button"); node.className = `icon-action ${className}`.trim();
  node.setAttribute("aria-label", label); node.title = label; node.dataset.tooltip = label;
  node.innerHTML = `<ha-icon icon="${icon}"></ha-icon>`;
  node.disabled = busy; node.addEventListener("click", action); return node;
}

export function recordingItem(item, context) {
  const row = document.createElement("article"); row.className = "item";
  const selector = document.createElement("label"); selector.className = "select-item";
  const checkbox = document.createElement("input"); checkbox.type = "checkbox";
  checkbox.checked = Boolean(context.selected); checkbox.disabled = context.busy || ["pending", "recording"].includes(item.status);
  checkbox.setAttribute("aria-label", `Seleziona registrazione ${item.recording_id}`);
  checkbox.addEventListener("change", () => context.select(checkbox.checked));
  selector.append(checkbox);
  const date = new Date(item.started_at || item.requested_at).toLocaleString("it-IT");
  const size = item.bytes ? `${(item.bytes / 1024 / 1024).toFixed(1)} MB` : "—";
  const duration = item.actual_duration_seconds || item.requested_duration_seconds;
  const detail = document.createElement("div"); const title = document.createElement("strong");
  title.textContent = date;
  const meta = document.createElement("div"); meta.className = "meta";
  meta.textContent = `${STATUS[item.status] || item.status} · ${Number(duration).toFixed(1)} s · ${size}`;
  detail.append(title, meta);
  const tags = context.tags?.(); if (tags) detail.append(tags);
  const actions = document.createElement("div"); actions.className = "item-actions";
  if (item.status === "ready") {
    if (context.provider === "ezviz") {
      actions.append(button("mdi:play", "Riproduci", context.play, context.busy));
    }
    actions.append(button("mdi:download", "Scarica", context.download, context.busy));
    actions.append(button("mdi:cloud-upload", "Backup NFS", context.backup, context.busy));
    actions.append(button("mdi:playlist-plus", "Aggiungi alle liste", context.lists, context.busy));
  }
  if (!["pending", "recording"].includes(item.status)) {
    actions.append(button("mdi:delete-outline", "Elimina", context.remove, context.busy, "danger"));
  }
  row.append(selector, detail, actions);
  if (context.picker) row.append(context.picker);
  return row;
}
