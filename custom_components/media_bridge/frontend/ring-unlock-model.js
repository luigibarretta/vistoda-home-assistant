// Pure view model for the read-only Ring unlock type sensor (Vistoda Ring 0.16+).
// Older engines create no sensor, so every caller must accept a null result.
export const UNLOCK_LABELS = { direct: "Diretta", ring_to_open: "Ring-to-Open" };

export function ringUnlockView(state) {
  if (!state || state.state === "unavailable") return null;
  const mode = typeof state.state === "string" && state.state !== "unknown" ? state.state : "";
  const raw = state.attributes?.duration_seconds;
  const duration = Number.isInteger(raw) && raw >= 0 ? raw : null;
  if (!mode && duration === null) return null;
  return {
    mode,
    // Unknown future modes are shown verbatim instead of being guessed.
    label: UNLOCK_LABELS[mode] || mode,
    duration,
    ringToOpen: mode === "ring_to_open" || state.attributes?.ring_to_open_enabled === true,
  };
}
