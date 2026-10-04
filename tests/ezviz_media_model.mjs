import assert from "node:assert/strict";
import test from "node:test";
import { ADVANCED_COPY } from "../custom_components/media_bridge/frontend/panel-copy.js";
import {
  KEY_SOURCE_LABELS, RECORD_LABELS, STORAGE_LABELS, capacityText, clampDay, dayRange, encryptionView, isoDay,
  recordRows, storageView,
} from "../custom_components/media_bridge/frontend/ezviz-media-model.js";

test("encryption view warns only when encrypted video has no key", () => {
  assert.equal(encryptionView(null), null);
  assert.equal(encryptionView({ video_encrypted: true, key_source: "none" }).warning, true);
  const option = encryptionView({ video_encrypted: true, key_source: "option" });
  assert.equal(option.warning, false);
  assert.equal(option.source, KEY_SOURCE_LABELS.option);
  assert.equal(encryptionView({ video_encrypted: false, key_source: "none" }).warning, false);
  const unknown = encryptionView({ video_encrypted: null, key_source: "future" });
  assert.deepEqual([unknown.encrypted, unknown.keySource, unknown.label], [null, null, "Sconosciuta"]);
});

test("storage view prefers the live sensor and tolerates unknown statuses", () => {
  assert.equal(storageView(null, undefined), null);
  const cached = storageView({ status: "ok", capacity_mb: 30436 });
  assert.deepEqual([cached.status, cached.capacityMb, cached.problem], ["ok", 30436, false]);
  const live = storageView({ status: "ok", capacity_mb: 1 }, { state: "unformatted", attributes: { capacity_mb: null } });
  assert.deepEqual([live.status, live.capacityMb, live.problem], ["unformatted", null, true]);
  assert.equal(storageView({ status: "ok" }, { state: "unavailable" }).status, "ok");
  assert.equal(storageView({ status: "melted" }).status, "unknown");
  assert.equal(capacityText(512), "512 MB");
  assert.equal(capacityText(30436, "en-US"), "29.7 GB");
  assert.equal(capacityText(null), "");
});

test("the day picker is limited to the last seven days", () => {
  const range = dayRange(new Date(2026, 9, 4, 0, 30));
  assert.deepEqual(range, { min: "2026-09-28", max: "2026-10-04" });
  assert.equal(clampDay("2026-09-28", range), "2026-09-28");
  assert.equal(clampDay("2026-09-27", range), "2026-10-04");
  assert.equal(clampDay("2026-10-05", range), "2026-10-04");
  assert.equal(clampDay("04/10/2026", range), "2026-10-04");
  assert.equal(isoDay(new Date(2026, 0, 2)), "2026-01-02");
});

test("record rows are bounded, sorted and typed", () => {
  const rows = recordRows([
    { start: 200, end: 260, type: "continuous" },
    { start: 100, end: 160, type: "event" },
    { start: 300, end: 200, type: "event" },
    { start: "x", end: 1 },
    { start: 400, end: 460, type: "future" },
  ], "en-GB");
  assert.deepEqual(rows.map((row) => [row.start, row.type]), [[100, "event"], [200, "continuous"], [400, "other"]]);
  assert.match(rows[0].text, /^\d{2}:\d{2}–\d{2}:\d{2}$/);
  assert.equal(recordRows(Array.from({ length: 600 }, (_, start) => ({ start, end: start }))).length, 500);
  assert.deepEqual(recordRows(null), []);
});

test("every media label is translated", () => {
  const labels = [...Object.values(KEY_SOURCE_LABELS), ...Object.values(STORAGE_LABELS), ...Object.values(RECORD_LABELS),
    "Attivata", "Disattivata", "Sconosciuta"];
  for (const label of labels) assert.ok(Object.hasOwn(ADVANCED_COPY, label), label);
});
