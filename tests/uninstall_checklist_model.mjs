import assert from "node:assert/strict";
import test from "node:test";
import { ADVANCED_COPY } from "../custom_components/media_bridge/frontend/panel-copy.js";
import { CHECKLIST, blinkPrograms, checklistSections } from "../custom_components/media_bridge/frontend/uninstall-checklist-model.js";

const info = (providers) => ({ providers });

test("only configured providers get a checklist section", () => {
  assert.deepEqual(checklistSections(null), []);
  const sections = checklistSections(info({ ring: { configured: true }, blink: { configured: false } }));
  assert.deepEqual(sections.map((item) => item.provider), ["ring"]);
  assert.ok(sections[0].items.every((item) => item.state === "todo" && item.note === ""));
});

test("EZVIZ status is computed from already loaded native metadata only", () => {
  const linked = { device_name: "Spioncino", control_source: "native",
    native_entities: [{ entity_id: "binary_sensor.cam_enc", role: "encrypted" }] };
  const [ok] = checklistSections(info({ ezviz: { configured: true, entries: [linked] } }),
    { "binary_sensor.cam_enc": { state: "on" } });
  assert.deepEqual(ok.items.map((item) => item.state), ["warn", "ok", "todo"]);
  assert.equal(ok.items[0].note, "Crittografia video attiva");
  // Delegated without the official integration: needs attention.
  const [missing] = checklistSections(info({ ezviz: { configured: true,
    entries: [{ entry_id: "x", control_source: "native" }] } }));
  assert.deepEqual(missing.items.map((item) => item.state), ["todo", "warn", "todo"]);
  // Standalone before the app answered: still to verify, never "native missing".
  const [pending] = checklistSections(info({ ezviz: { configured: true, entries: [{ entry_id: "y" }] } }));
  assert.deepEqual(pending.items.map((item) => item.state), ["todo", "todo", "todo"]);
  const [none] = checklistSections(info({ ezviz: { configured: true, entries: [] } }));
  assert.equal(none.items[1].state, "todo");
});

test("every checklist text and note is translated", () => {
  const notes = ["Comandi delegati all’integrazione EZVIZ ufficiale",
    "Integrazione EZVIZ ufficiale non disponibile: ripristinala o disattiva la delega", "Crittografia video attiva",
    "Verificato", "Da controllare", "Da fare"];
  for (const text of [...Object.values(CHECKLIST).flat(), ...notes]) assert.ok(Object.hasOwn(ADVANCED_COPY, text), text);
});

test("Blink schedules come from enabled program switches only", () => {
  const states = {
    "switch.programma_notte": { state: "on", attributes: { program_id: 7, friendly_name: "Programma: Notte" } },
    "switch.programma_giorno": { state: "off", attributes: { program_id: 8, friendly_name: "Programma: Giorno" } },
    "switch.other": { state: "on", attributes: {} },
    "sensor.program": { state: "on", attributes: { program_id: 9 } },
  };
  const [blink] = checklistSections(info({ blink: { configured: true } }), states);
  assert.equal(blink.items[0].state, "warn");
  assert.deepEqual(blink.items[0].links, [{ entityId: "switch.programma_notte", name: "Programma: Notte" }]);
  assert.deepEqual(blinkPrograms(states).map((item) => item.entityId), ["switch.programma_giorno", "switch.programma_notte"]);
  states["switch.programma_notte"].state = "off";
  const [off] = checklistSections(info({ blink: { configured: true } }), states);
  assert.deepEqual([off.items[0].state, off.items[0].links], ["ok", []]);
  const [none] = checklistSections(info({ blink: { configured: true } }), {});
  assert.equal(none.items[0].state, "todo");
});

test("Ring unlock type feeds the unlock item", () => {
  const ring = (state) => checklistSections(info({ ring: { configured: true, entries: [{ unlock_entity_id: "sensor.unlock" }] } }),
    { "sensor.unlock": state })[0].items[1];
  assert.equal(ring({ state: "direct", attributes: {} }).state, "ok");
  assert.equal(ring({ state: "ring_to_open", attributes: {} }).state, "warn");
  assert.equal(ring({ state: "keypad", attributes: {} }).state, "todo");
  assert.equal(ring(undefined).state, "todo");
});

test("EZVIZ encryption and microSD come from the app status when known", () => {
  const ezviz = (media, states = {}) => checklistSections(info({ ezviz: { configured: true,
    entries: [{ device_name: "Spioncino", media, microsd_entity_id: "sensor.sd", controls: { supported: true } }] } }),
    states)[0].items;
  const none = ezviz({ encryption: { video_encrypted: true, key_source: "none" }, storage: { status: "ok" } });
  assert.deepEqual(none.map((item) => item.state), ["warn", "ok", "ok"]);
  const option = ezviz({ encryption: { video_encrypted: true, key_source: "option" }, storage: { status: "no_card" } });
  assert.deepEqual(option.map((item) => item.state), ["ok", "ok", "warn"]);
  assert.equal(option[2].note, "Nessuna microSD inserita");
  const live = ezviz({ encryption: null, storage: { status: "ok" } }, { "sensor.sd": { state: "error", attributes: {} } });
  assert.deepEqual([live[0].state, live[2].state, live[2].note], ["todo", "warn", "Errore della microSD"]);
  assert.equal(ezviz({ encryption: null, storage: { status: "unknown" } })[2].state, "todo");
  const notes = [...ezviz({ encryption: { video_encrypted: true, key_source: "cloud" }, storage: { status: "unformatted" } }),
    ...option, ...none].map((item) => item.note).filter(Boolean);
  for (const note of notes) assert.ok(Object.hasOwn(ADVANCED_COPY, note), note);
});

test("EZVIZ controls item: ok when standalone works, explicit hints otherwise", () => {
  const ezviz = (entries) => checklistSections(info({ ezviz: { configured: true, entries } }))[0].items[1];
  const app = { entry_id: "a", control_source: "vistoda", controls: { supported: true } };
  const old = { entry_id: "b", control_source: "vistoda", controls: { supported: false } };
  const outdated = "Aggiorna l’app Vistoda EZVIZ alla 0.10 o attiva la delega all’integrazione EZVIZ ufficiale";
  assert.deepEqual(ezviz([app]), { text: CHECKLIST.ezviz[1], state: "ok",
    note: "Controlli tramite l’app Vistoda EZVIZ", links: [] });
  // A standalone entry never counts the native integration, even when linked.
  assert.deepEqual([ezviz([app, old]).state, ezviz([app, old]).note], ["warn", outdated]);
  assert.equal(ezviz([app, { ...old, device_name: "Spioncino" }]).note, outdated);
  const delegated = { entry_id: "c", control_source: "native", device_name: "Spioncino", delegate_available: true };
  assert.equal(ezviz([app, delegated]).note, "Controlli tramite l’app Vistoda EZVIZ");
  assert.equal(ezviz([delegated]).note, "Comandi delegati all’integrazione EZVIZ ufficiale");
  assert.equal(ezviz([{ ...delegated, delegate_available: false }]).state, "warn");
  assert.equal(ezviz([app, { entry_id: "d" }]).state, "todo");
  for (const note of ["Controlli tramite l’app Vistoda EZVIZ", outdated]) assert.ok(Object.hasOwn(ADVANCED_COPY, note), note);
});

test("standalone entries never use the official integration's encryption sensor", () => {
  const native = [{ entity_id: "binary_sensor.cam_enc", role: "encrypted" }];
  const item = (control_source) => checklistSections(info({ ezviz: { configured: true,
    entries: [{ control_source, native_entities: native }] } }), { "binary_sensor.cam_enc": { state: "on" } })[0].items[0];
  assert.equal(item("vistoda").state, "todo");
  assert.equal(item("native").note, "Crittografia video attiva");
});
