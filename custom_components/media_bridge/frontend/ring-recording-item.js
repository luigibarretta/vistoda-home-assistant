function action(icon, label, className, disabled, expanded, callback) {
  const button = document.createElement("button");
  button.className = className;
  button.disabled = disabled;
  button.innerHTML = `<ha-icon icon="${icon}"></ha-icon><span>${label}</span>`;
  button.setAttribute("aria-label", label);
  if (expanded !== null) button.setAttribute("aria-expanded", String(expanded));
  button.addEventListener("click", callback);
  return button;
}

function actions(recording, context) {
  const wrap = document.createElement("div");
  wrap.className = "row-actions";
  const playLabel = context.playerOpen ? "Chiudi player" : "Riproduci";
  wrap.append(
    action(context.playerOpen ? "mdi:close-circle-outline" : "mdi:play-circle-outline",
      playLabel, "row-action", context.busy, context.playerOpen, () => context.onPlay(recording)),
    action("mdi:playlist-plus", "Liste", "row-action", context.busy,
      context.listsOpen, () => context.onLists(recording)),
    action("mdi:information-outline", "Info", "row-action", context.busy,
      context.infoOpen, () => context.onInfo(recording)),
    action("mdi:delete-outline", "Elimina", "danger row-action", context.busy,
      null, () => context.onDelete(recording)),
  );
  return wrap;
}

function detailRow(detail) {
  const row = document.createElement("tr");
  row.className = "detail-row";
  const cell = document.createElement("td");
  cell.colSpan = 4;
  cell.append(detail);
  row.append(cell);
  return row;
}

export function recordingTableNodes(recording, context) {
  const row = document.createElement("tr");
  for (const value of [context.date, context.duration, context.size]) {
    const cell = document.createElement("td");
    cell.textContent = value;
    row.append(cell);
  }
  const cell = document.createElement("td");
  cell.append(actions(recording, context));
  row.append(cell);
  return context.detail ? [row, detailRow(context.detail)] : [row];
}

export function recordingCard(recording, context) {
  const card = document.createElement("article");
  card.className = "recording-card";
  const heading = document.createElement("div");
  heading.className = "recording-heading";
  const date = document.createElement("strong");
  date.textContent = context.date;
  const meta = document.createElement("span");
  meta.className = "hint";
  meta.textContent = `${context.duration} · ${context.size}`;
  heading.append(date, meta);
  card.append(heading);
  if (context.listNames.length) {
    const tags = document.createElement("div");
    tags.className = "list-tags";
    for (const name of context.listNames) {
      const tag = document.createElement("span");
      tag.textContent = name;
      tags.append(tag);
    }
    card.append(tags);
  }
  card.append(actions(recording, context));
  if (context.detail) {
    const detail = document.createElement("div");
    detail.className = "card-detail";
    detail.append(context.detail);
    card.append(detail);
  }
  return card;
}
