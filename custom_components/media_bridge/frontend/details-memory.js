// Keeps <details> sections as the user left them when a list is rebuilt.
export function rememberOpen(details, key, closed) {
  const id = String(key);
  details.open = !closed.has(id);
  details.addEventListener("toggle", () => (details.open ? closed.delete(id) : closed.add(id)));
}
