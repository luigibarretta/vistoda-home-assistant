import assert from "node:assert/strict";
import test from "node:test";
import { ADVANCED_COPY, copy } from "../custom_components/media_bridge/frontend/panel-copy.js";
import {
  batteryPowered, errorLabel, recommendedInterval, resultLabel, scheduleFor, syncChoice, syncChoices, syncNotice,
} from "../custom_components/media_bridge/frontend/scenetrove-sync-model.js";

const battery = { controls: { battery_percent: 1 } };
const mains = { controls: { battery_percent: null } };

test("battery cameras are recommended a 6-hour interval, mains cameras 1 hour", () => {
  assert.equal(batteryPowered(battery), true);
  assert.equal(batteryPowered(mains), false);
  assert.equal(batteryPowered(null), false);
  assert.equal(recommendedInterval(battery), 360);
  assert.equal(recommendedInterval(mains), 60);
});

test("the select offers off and the five intervals, keeping a foreign SceneTrove value visible", () => {
  assert.deepEqual(syncChoices({ enabled: true, interval_minutes: 360 }).map((c) => c.value),
    ["off", "60", "180", "360", "720", "1440"]);
  assert.deepEqual(syncChoices({ enabled: true, interval_minutes: 30 }).map((c) => c.value),
    ["off", "30", "60", "180", "360", "720", "1440"]);
  assert.equal(copy("en", "Ogni {p0} min", { p0: 30 }), "Every 30 min");
  assert.equal(syncChoice({ enabled: false, interval_minutes: 360 }), "off");
  assert.equal(syncChoice({ enabled: true, interval_minutes: 720 }), "720");
});

test("choices become bounded requests; off sends the current interval back unchanged", () => {
  assert.deepEqual(scheduleFor("360", null, battery), { enabled: true, interval_minutes: 360 });
  assert.deepEqual(scheduleFor("off", { interval_minutes: 720 }, battery), { enabled: false, interval_minutes: 720 });
  for (const custom of [15, 30, 90, 1440]) {
    assert.deepEqual(scheduleFor("off", { enabled: true, interval_minutes: custom }, battery),
      { enabled: false, interval_minutes: custom }, "a custom SceneTrove interval is never overwritten");
  }
  for (const invalid of [undefined, 14, 1441, 30.5, "60"]) {
    assert.deepEqual(scheduleFor("off", { interval_minutes: invalid }, battery), { enabled: false, interval_minutes: 360 });
    assert.deepEqual(scheduleFor("off", { interval_minutes: invalid }, mains), { enabled: false, interval_minutes: 60 });
  }
  assert.equal(scheduleFor("30", null, mains), null, "a value the server would refuse is never sent");
});

test("results, errors and notices are authored, translated copy", () => {
  for (const result of ["ok", "camera_offline", "bridge_busy", "bridge_error", "unavailable", "<b>"]) {
    assert.ok(Object.hasOwn(ADVANCED_COPY, resultLabel(result)), result);
  }
  for (const code of ["scenetrove_unauthorized", "scenetrove_unknown_device", "scenetrove_live_source_required",
    "scenetrove_unreachable", "scenetrove_unsupported_version", "scenetrove_redirected", "unauthorized",
    "anything_else"]) {
    assert.ok(Object.hasOwn(ADVANCED_COPY, errorLabel(code)), code);
  }
  assert.equal(syncNotice({ enabled: true, available: true }), "");
  assert.equal(syncNotice({ enabled: false, available: false }), "", "an intentionally disabled sync is quiet");
  assert.ok(Object.hasOwn(ADVANCED_COPY, syncNotice({ enabled: true, available: false })));
  for (const label of syncChoices({ enabled: false }).map((c) => c.label)) assert.ok(Object.hasOwn(ADVANCED_COPY, label), label);
});
