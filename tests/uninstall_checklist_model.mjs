import assert from "node:assert/strict";
import test from "node:test";
import { ADVANCED_COPY } from "../custom_components/media_bridge/frontend/panel-copy.js";
import { CHECKLIST, checklistSections } from "../custom_components/media_bridge/frontend/uninstall-checklist-model.js";

const info = (providers) => ({ providers });

test("only configured providers get a checklist section", () => {
  assert.deepEqual(checklistSections(null), []);
  const sections = checklistSections(info({ ring: { configured: true }, blink: { configured: false } }));
  assert.deepEqual(sections.map((item) => item.provider), ["ring"]);
  assert.ok(sections[0].items.every((item) => item.state === "todo" && item.note === ""));
});

test("EZVIZ status is computed from already loaded native metadata only", () => {
  const linked = { device_name: "Spioncino",
    native_entities: [{ entity_id: "binary_sensor.cam_enc", role: "encrypted" }] };
  const [ok] = checklistSections(info({ ezviz: { configured: true, entries: [linked] } }),
    { "binary_sensor.cam_enc": { state: "on" } });
  assert.deepEqual(ok.items.map((item) => item.state), ["warn", "ok", "todo"]);
  assert.equal(ok.items[0].note, "Crittografia video attiva");
  const [missing] = checklistSections(info({ ezviz: { configured: true, entries: [{ entry_id: "x" }] } }));
  assert.deepEqual(missing.items.map((item) => item.state), ["todo", "warn", "todo"]);
  const [none] = checklistSections(info({ ezviz: { configured: true, entries: [] } }));
  assert.equal(none.items[1].state, "todo");
});

test("every checklist text and note is translated", () => {
  const notes = ["Integrazione nativa collegata", "Integrazione nativa non collegata", "Crittografia video attiva",
    "Verificato", "Da controllare", "Da fare"];
  for (const text of [...Object.values(CHECKLIST).flat(), ...notes]) assert.ok(Object.hasOwn(ADVANCED_COPY, text), text);
});
