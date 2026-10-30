import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";
import { ADVANCED_COPY, copy } from "../custom_components/media_bridge/frontend/panel-copy.js";
import {
  ALARM_CATEGORIES,
  alarmCategory,
  alarmIsoTime,
  alarmPage,
  alarmVideo,
  alarmPicturePath,
  alarmRows,
  alarmTimeText,
} from "../custom_components/media_bridge/frontend/ezviz-alarm-model.js";

const picture = "/api/media_bridge/ezviz/01J9ENTRY/alarms/alarm-2.jpg";

test("alarm rows are newest first, bounded and normalized", () => {
  const rows = alarmRows([
    { alarm_id: "alarm-1", occurred_at: 100, category: "person", title: "Persona", picture: null },
    { alarm_id: "alarm-2", occurred_at: 300, category: "unknown", title: "x".repeat(400), picture },
    { alarm_id: "alarm-3", occurred_at: 200, category: "doorbell", title: 7, picture: "https://evil.example/a.jpg" },
    { alarm_id: "", occurred_at: 400 },
    { alarm_id: "bad-time", occurred_at: -1 },
    null,
  ], 2);
  assert.deepEqual(rows.map((row) => row.id), ["alarm-2", "alarm-3"]);
  assert.equal(rows[0].category, "other");
  assert.equal(rows[0].label, "Altro allarme");
  assert.equal(rows[0].title.length, 160);
  assert.equal(rows[0].picture, picture);
  assert.equal(rows[1].icon, "mdi:doorbell");
  assert.equal(rows[1].title, "");
  assert.equal(rows[1].picture, null, "foreign picture URLs are never loaded");
  assert.deepEqual(alarmRows(undefined), []);
});

test("picture paths accept only the integration's own relative route", () => {
  assert.equal(alarmPicturePath(picture), picture);
  for (const value of [
    "/api/media_bridge/ezviz/01J9ENTRY/alarms/../secret.jpg",
    "/api/media_bridge/ezviz/01J9ENTRY/alarms/a.b.jpg",
    "//evil.example/api/media_bridge/ezviz/x/alarms/y.jpg",
    "/api/media_bridge/ezviz/01J9ENTRY/alarms/alarm.png",
    42,
  ]) assert.equal(alarmPicturePath(value), null, String(value));
  assert.equal(alarmCategory("vehicle"), "vehicle");
  assert.equal(alarmCategory("__proto__"), "other");
});

test("every alarm category and component string has an English translation", async () => {
  for (const [, label] of Object.values(ALARM_CATEGORIES)) {
    assert.ok(Object.hasOwn(ADVANCED_COPY, label), label);
  }
  assert.equal(copy("en", "Campanello"), "Doorbell");
  assert.equal(copy("it", "Eventi"), "Eventi");
  assert.equal(copy("en", "Eventi"), "Events");
  const source = await readFile(new URL("../custom_components/media_bridge/frontend/ezviz-alarms.js", import.meta.url), "utf8");
  assert.match(source, /media_bridge\/ezviz\/alarms\/list/);
  assert.match(source, /auth\/sign_path/);
});

test("alarm times show the date only for earlier days", () => {
  const now = Date.UTC(2026, 9, 4, 18, 0);
  const today = Date.UTC(2026, 9, 4, 7, 5) / 1000;
  const earlier = Date.UTC(2026, 9, 2, 7, 5) / 1000;
  assert.equal(alarmTimeText(today, "it-IT", now, "UTC"), "07:05");
  assert.match(alarmTimeText(earlier, "en-GB", now, "UTC"), /^2 Oct,? 07:05$/);
  assert.equal(alarmTimeText(Number.NaN), "");
  assert.equal(alarmIsoTime(today), "2026-10-04T07:05:00.000Z");
});

test("alarm pages stay open-ended until the app reports no older batch", () => {
  const rows = Array.from({ length: 50 }, (_, index) => index);
  const first = alarmPage(rows, 1, 25, false);
  assert.deepEqual([first.rows.length, first.page, first.totalPages], [25, 1, null]);
  assert.deepEqual([first.hasPrevious, first.hasNext, first.needsMore], [false, true, false]);
  const second = alarmPage(rows, 2, 25, false);
  assert.deepEqual([second.rows.at(0), second.hasNext, second.needsMore], [25, true, false]);
  const third = alarmPage(rows, 3, 25, false);
  assert.deepEqual([third.rows.length, third.needsMore], [0, true], "page 3 waits for the next batch");
  const partial = alarmPage(rows, 2, 100, false);
  assert.deepEqual([partial.page, partial.needsMore], [2, true]);
});

test("complete alarm history clamps pages and knows the page count", () => {
  const rows = Array.from({ length: 123 }, (_, index) => index);
  const last = alarmPage(rows, 99, 50, true);
  assert.deepEqual([last.page, last.totalPages, last.rows.length], [3, 3, 23]);
  assert.deepEqual([last.hasPrevious, last.hasNext, last.needsMore], [true, false, false]);
  const empty = alarmPage([], 4, 10, true);
  assert.deepEqual([empty.page, empty.totalPages, empty.rows, empty.hasNext], [1, 1, [], false]);
  assert.deepEqual(alarmPage(undefined, 0, 0, true).rows, []);
});

test("archive items become card rows with their own picture route", () => {
  const archived = "/api/media_bridge/events/01J9ENTRY/20261028T190000Z-evt-1.jpg";
  const rows = alarmRows([
    { id: "20261028T190000Z-evt-1", alarm_id: "evt-1", occurred_at: 1793214000, category: "person",
      title: "Persona", picture: archived },
    { id: "20261028T200000Z-evt-2", alarm_id: "evt-2", occurred_at: 1793217600, category: "doorbell",
      title: "", picture: "/api/media_bridge/events/01J9ENTRY/../../secret.jpg" },
  ], 10);
  assert.deepEqual(rows.map((row) => row.id), ["evt-2", "evt-1"]);
  assert.equal(rows[1].picture, archived);
  assert.equal(rows[0].picture, null, "traversal in an archive route is refused");
  assert.equal(alarmPicturePath("/api/media_bridge/events/01J9ENTRY/evt-1.jpg"), null,
    "archive pictures carry the timestamped event name");
});

const T = 1793214000; // 2026-10-28T19:00:00Z
const live = { recording_id: "live-1", status: "ready", started_at: "2026-10-28T18:59:50Z", actual_duration_seconds: 30 };
const card = { recording_id: "sd-1", status: "ready", source: "sd", sd_start: T + 100, sd_end: T + 160 };

test("a covering recording is played", () => {
  assert.deepEqual(alarmVideo([card, live], T), { kind: "play", recording: live });
  assert.deepEqual(alarmVideo([live, card], T + 130), { kind: "play", recording: card });
});

test("edges of a recording cover the event", () => {
  assert.equal(alarmVideo([live], T - 10).kind, "play");
  assert.equal(alarmVideo([live], T + 20).kind, "play");
  assert.equal(alarmVideo([card], T + 160).kind, "play");
  assert.equal(alarmVideo([card], T + 161).kind, "save");
});

test("otherwise the microSD window is offered", () => {
  assert.deepEqual(alarmVideo([], T), { kind: "save", start: T - 10, end: T + 50 });
  assert.deepEqual(alarmVideo(undefined, T), { kind: "save", start: T - 10, end: T + 50 });
});

test("failed or pending recordings are ignored", () => {
  for (const status of ["failed", "pending", "recording"]) {
    assert.equal(alarmVideo([{ ...live, status }], T).kind, "save", status);
  }
  assert.equal(alarmVideo([{ ...live, actual_duration_seconds: null }], T).kind, "save");
});

test("every event modal string has an English translation", async () => {
  const source = await readFile(
    new URL("../custom_components/media_bridge/frontend/ezviz-alarm-dialog.js", import.meta.url), "utf8");
  const keys = [...source.matchAll(/copy\(this, "([^"]+)"/g)].map((match) => match[1]);
  assert.ok(keys.length >= 7, "the modal uses the copy catalog");
  for (const key of keys) assert.ok(Object.hasOwn(ADVANCED_COPY, key), key);
  assert.match(source, /media_bridge\/ezviz\/recordings\/create_sd/);
  assert.match(source, /showModal\(\)/);
});
