// Deleting archived copies: the ids to send and the confirmation to ask first.
// Shared clips are SceneTrove's copy too, so the confirmation says so.
export function deletePlan(items) {
  const shared = items.some((item) => item.shared);
  return {
    ids: items.map((item) => item.id),
    prompt: shared ? "Eliminare {p0} copie? Quelle condivise spariscono anche da SceneTrove." : "Eliminare {p0} copie archiviate?",
  };
}
