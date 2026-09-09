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
  let current = settings; const applied = [];
  try {
    for (const [key, value] of draft) {
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
