import assert from "node:assert/strict";
import test from "node:test";

const frontend = (name) => new URL(`../custom_components/media_bridge/frontend/${name}`, import.meta.url);
const { saveInterval, SD_SAVE_SECONDS } = await import(frontend("ezviz-sd-save.js"));
const { recordedAt } = await import(frontend("provider-recording-model.js"));
const { localize, localizeCount } = await import(frontend("panel-localize.js"));

test("a listed microSD clip is saved whole, or from its start up to the bridge bound", () => {
  assert.deepEqual(saveInterval({ start: 100, end: 130 }), { start: 100, end: 130 });
  assert.deepEqual(saveInterval({ start: 100, end: 100 + 600 }), { start: 100, end: 100 + SD_SAVE_SECONDS });
  // An instantaneous event still asks for a short clip.
  assert.deepEqual(saveInterval({ start: 100, end: 100 }), { start: 100, end: 110 });
});

test("archive rows show when microSD media was recorded, not requested", () => {
  const sd = { source: "sd", sd_start: 1_791_108_000, requested_at: "2026-10-24T06:00:00Z" };
  assert.equal(recordedAt(sd), 1_791_108_000_000);
  const live = { started_at: "2026-10-24T06:00:01Z", requested_at: "2026-10-24T06:00:00Z" };
  assert.equal(recordedAt(live), "2026-10-24T06:00:01Z");
  assert.equal(recordedAt({ source: "sd", sd_start: "x", requested_at: "r" }), "r");
});

test("device and camera counts use singular and plural forms", () => {
  const count = (locale, devices, cameras) => localize(locale, "deviceCount", {
    devices: localizeCount(locale, "device", devices), cameras: localizeCount(locale, "camera", cameras) });
  assert.equal(count("en", 2, 1), "2 devices · 1 camera");
  assert.equal(count("en", 1, 0), "1 device · 0 cameras");
  assert.equal(count("it", 1, 1), "1 dispositivo · 1 telecamera");
  assert.equal(count("it", 8, 6), "8 dispositivi · 6 telecamere");
});
