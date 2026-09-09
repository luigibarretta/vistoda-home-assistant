export const GRID_COLUMNS = 20;
export const GRID_ROWS = 15;
const MICRO_COLUMNS = 4;
const MICRO_ROWS = 3;

export function gridCell(x, y) {
  return {
    basic: Math.floor(y / MICRO_ROWS) * 5 + Math.floor(x / MICRO_COLUMNS),
    bit: (y % MICRO_ROWS) * MICRO_COLUMNS + (x % MICRO_COLUMNS),
  };
}

export function activityEnabled(masks, x, y) {
  const { basic, bit } = gridCell(x, y);
  return Boolean((masks[basic] || 0) & (1 << bit));
}

export function setActivity(masks, x, y, enabled) {
  const next = [...masks];
  const { basic, bit } = gridCell(x, y);
  next[basic] = enabled ? (next[basic] | (1 << bit)) : (next[basic] & ~(1 << bit));
  return next;
}

export function privacyContains(zones, x, y) {
  return zones.some((zone) => x >= zone.x && x < zone.x + zone.w
    && y >= zone.y && y < zone.y + zone.h);
}

export function rectangleFromCells(start, end) {
  const x = Math.min(start.x, end.x); const y = Math.min(start.y, end.y);
  return { x, y, w: Math.abs(start.x - end.x) + 1, h: Math.abs(start.y - end.y) + 1 };
}

export function allActivityDisabled(masks) { return masks.every((mask) => mask === 0); }

export function sameZoneDraft(zones, masks, privacy) {
  return JSON.stringify(zones?.activity_masks) === JSON.stringify(masks)
    && JSON.stringify(zones?.privacy_zones) === JSON.stringify(privacy);
}
