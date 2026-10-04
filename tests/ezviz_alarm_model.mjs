import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";
import { ADVANCED_COPY, copy } from "../custom_components/media_bridge/frontend/panel-copy.js";
import {
  ALARM_CATEGORIES,
  alarmCategory,
  alarmIsoTime,
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
