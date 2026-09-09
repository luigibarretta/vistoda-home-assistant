const STATUS = {
  pending: "In attesa", recording: "Registrazione in corso", ready: "Pronta", failed: "Non riuscita",
};

function button(label, action, busy, className = "") {
  const node = document.createElement("button"); node.textContent = label; node.className = className;
  node.disabled = busy; node.addEventListener("click", action); return node;
}

export function recordingItem(item, context) {
  const row = document.createElement("article"); row.className = "item";
  const date = new Date(item.started_at || item.requested_at).toLocaleString("it-IT");
  const size = item.bytes ? `${(item.bytes / 1024 / 1024).toFixed(1)} MB` : "—";
  const duration = item.actual_duration_seconds || item.requested_duration_seconds;
  const detail = document.createElement("div"); const title = document.createElement("strong");
  title.textContent = date;
  const meta = document.createElement("div"); meta.className = "meta";
  meta.textContent = `${STATUS[item.status] || item.status} · ${Number(duration).toFixed(1)} s · ${size}`;
  detail.append(title, meta);
  const actions = document.createElement("div"); actions.className = "item-actions";
  if (item.status === "ready") {
    if (context.provider === "ezviz") {
      actions.append(button("Riproduci", context.play, context.busy));
    }
    actions.append(button("Scarica", context.download, context.busy));
    actions.append(button("Backup NFS", context.backup, context.busy));
  }
  if (!["pending", "recording"].includes(item.status)) {
    actions.append(button("Elimina", context.remove, context.busy, "danger"));
  }
  row.append(detail, actions); return row;
}
