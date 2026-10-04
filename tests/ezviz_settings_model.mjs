import assert from "node:assert/strict";
import test from "node:test";
import { ADVANCED_COPY } from "../custom_components/media_bridge/frontend/panel-copy.js";
import {
  GROUPS, OPTION_LABELS, PROVIDER_LABELS, settingsSections,
} from "../custom_components/media_bridge/frontend/ezviz-settings-model.js";

const entity = (entity_id, extra = {}) => ({ entity_id, domain: entity_id.split(".")[0], name: entity_id, ...extra });
const section = (sections, key) => sections.find((item) => item.key === key);

test("arming group leads and holds per-camera defence plus the schedule", () => {
  const provider = [
    { key: "camera_defence", group: "arming", kind: "boolean", value: false },
    { key: "alarm_schedule", group: "arming", kind: "status", value: true },
  ];
  const entities = [
    entity("binary_sensor.piano", { role: "alarm_schedule" }),
    entity("number.sensibilita", { role: "detection_sensitivity" }),
    entity("binary_sensor.cifratura", { role: "encrypted" }),
  ];
  const sections = settingsSections(entities, provider);
  assert.equal(sections[0].key, "arming");
  assert.deepEqual(sections[0].provider.map((item) => item.key), ["camera_defence", "alarm_schedule"]);
  // The provider already shows the schedule, so the native duplicate is hidden.
  assert.deepEqual(sections[0].rows, []);
  // Localized entity ids still land in the right group thanks to the role.
  assert.deepEqual(section(sections, "detection").rows.map((item) => item.entity_id), ["number.sensibilita"]);
  assert.deepEqual(section(sections, "privacy").rows.map((item) => item.entity_id), ["binary_sensor.cifratura"]);
  assert.equal(section(sections, "other"), undefined);
});

test("native schedule sensor is kept when the provider cannot read it", () => {
  const sections = settingsSections([entity("binary_sensor.piano", { role: "alarm_schedule" })], []);
  assert.deepEqual(sections[0].rows.map((item) => item.entity_id), ["binary_sensor.piano"]);
});

test("PTZ buttons are never generic settings rows", () => {
  const ptz = ["up", "down", "left", "right"].map((direction) =>
    entity(`button.cam_${direction}`, { role: `ptz_${direction}` }));
  const sections = settingsSections([...ptz, entity("switch.cam_audio")], []);
  const rows = sections.flatMap((item) => item.rows.map((row) => row.entity_id));
  assert.deepEqual(rows, ["switch.cam_audio"]);
});

test("every group, provider and option label is translated", () => {
  const labels = [...GROUPS.map((group) => group[2]), ...Object.values(PROVIDER_LABELS),
    ...Object.values(OPTION_LABELS), "Altre impostazioni"];
  for (const label of labels) assert.ok(Object.hasOwn(ADVANCED_COPY, label) || label === "WDR", label);
});
