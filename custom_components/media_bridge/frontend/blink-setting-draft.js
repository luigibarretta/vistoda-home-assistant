function equal(left, right) { return JSON.stringify(left) === JSON.stringify(right); }

export function cameraDraft(drafts, alias) {
  if (!drafts.has(alias)) drafts.set(alias, new Map());
  return drafts.get(alias);
}

export function stagedField(field, draft) {
  return draft.has(field.key) ? { ...field, value: draft.get(field.key) } : field;
}

export function stageValue(settings, draft, key, value) {
  const original = settings?.settings?.find((field) => field.key === key);
  if (!original || equal(original.value, value)) draft.delete(key);
  else draft.set(key, value);
}

export function reconcileDraft(settings, draft) {
  for (const [key, value] of draft) stageValue(settings, draft, key, value);
}

async function update(hass, alias, current, key, value) {
  return hass.callWS({ type: "blink_live_bridge/camera/settings/update",
    alias, key, value, revision: current.revision });
}

export async function commitDraft(hass, alias, settings, draft) {
  const initialTemperature = ["temperature_min", "temperature_max"].some((key) =>
    settings.settings.find((field) => field.key === key)?.value === null);
  if (initialTemperature && (draft.has("temperature_min") || draft.has("temperature_max")
      || draft.get("temperature_alerts") === true)) {
    return initializeTemperature(hass, alias, settings, draft);
  }
  let current = settings; const applied = [];
  const changes = orderedChanges(settings, draft);
  try {
    for (const [key, value] of changes) {
      const original = settings.settings.find((field) => field.key === key);
      if (!original) throw new Error(`Setting ${key} disappeared`);
      current = await update(hass, alias, current, key, value);
      applied.push([key, original.value]);
    }
    return current;
  } catch (cause) {
    let rollbackFailed = false;
    for (const [key, value] of applied.reverse()) {
      try { current = await update(hass, alias, current, key, value); }
      catch (_error) { rollbackFailed = true; break; }
    }
    const error = new Error("Blink setting batch failed", { cause });
    error.rollbackFailed = rollbackFailed; throw error;
  }
}

async function initializeTemperature(hass, alias, settings, draft) {
  if ([...draft.keys()].some((key) => !key.startsWith("temperature_"))) {
    throw new Error("temperature_initialization_separate");
  }
  const value = Object.fromEntries(["temperature_min", "temperature_max"].map((key) =>
    [key, draft.get(key) ?? settings.settings.find((field) => field.key === key)?.value]));
  if (!Object.values(value).every(Number.isInteger)) throw new Error("temperature_missing");
  if (value.temperature_max - value.temperature_min < 10) throw new Error("temperature_gap");
  try {
    let current = await update(hass, alias, settings, "temperature_thresholds", value);
    if (draft.has("temperature_alerts")) {
      current = await update(hass, alias, current, "temperature_alerts", draft.get("temperature_alerts"));
    }
    return current;
  } catch (cause) {
    const error = new Error("Blink temperature initialization failed", {cause});
    // An absent upstream threshold cannot be restored through this API.
    error.rollbackFailed = true; throw error;
  }
}

export function orderedChanges(settings, draft) {
  const changes = Array.from(draft);
  const original = (key) => settings.settings.find((field) => field.key === key)?.value;
  const low = draft.get("temperature_min") ?? original("temperature_min");
  const high = draft.get("temperature_max") ?? original("temperature_max");
  if ((draft.has("temperature_min") || draft.has("temperature_max")) && high - low < 10) {
    throw new Error("temperature_gap");
  }
  // Expand the old interval before shrinking it; inverse rollback stays valid.
  const rank = ([key, value]) => {
    if (key === "temperature_alerts") return value ? 3 : -1;
    if (key === "temperature_min") return value < original(key) ? 0 : 2;
    if (key === "temperature_max") return value > original(key) ? 0 : 2;
    return 1;
  };
  return changes.sort((a, b) => rank(a) - rank(b));
}
