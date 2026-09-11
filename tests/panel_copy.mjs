import assert from "node:assert/strict";
import test from "node:test";
import { readdir, readFile } from "node:fs/promises";
import { ADVANCED_COPY, copy, localizeCopy } from "../custom_components/media_bridge/frontend/panel-copy.js";
import { BLINK_SETTING_META, BLINK_SETTING_SECTIONS, BLINK_OPTION_LABELS } from "../custom_components/media_bridge/frontend/blink-setting-schema.js";
import { videoQualityOptions, booleanStateText } from "../custom_components/media_bridge/frontend/blink-setting-model.js";
import { recordingStorageSummary } from "../custom_components/media_bridge/frontend/recording-storage.js";

test("advanced catalogs preserve placeholder contracts and source text", () => {
  const parameters = value => [...value.matchAll(/\{p\d+\}/g)].map(match => match[0]).sort();
  for (const [source, english] of Object.entries(ADVANCED_COPY)) {
    assert.ok(english.trim(), source);
    assert.deepEqual(parameters(english), parameters(source), source);
    assert.equal(copy("it", source), source);
    assert.equal(copy("de", source), english);
  }
  assert.equal(copy("en", "Future authored message"), "Future authored message", "missing copy fails safely");
  assert.equal(copy({ host: { _hass: { locale: { language: "it-IT" } } } }, "Salva"), "Salva");
  assert.equal(copy("en", "Nuovo nome per {p0}", { p0: "Elimina <script>" }), "New name for Elimina <script>");
});

test("every explicit static marker and copy call has a catalog entry", async () => {
  const directory = new URL("../custom_components/media_bridge/frontend/", import.meta.url);
  for (const file of (await readdir(directory)).filter(name => name.endsWith(".js") && !name.startsWith("panel-copy"))) {
    const source = await readFile(new URL(file, directory), "utf8");
    for (const pattern of [/data-copy(?:-[\w-]+)?="([^"$]+)"/g, /copy\([^,\n]+,\s*"([^"$]*)"/g]) {
      for (const [, key] of source.matchAll(pattern)) {
        assert.ok(Object.hasOwn(ADVANCED_COPY, key.replace(/&quot;/g, '"').replace(/&amp;/g, "&")), `${file}: ${key}`);
      }
    }
  }
});

test("all advanced Blink schema labels translate without altering unknown vendor values", () => {
  const labels = [...BLINK_SETTING_SECTIONS.flatMap(s => [s.title, s.description]),
    ...Object.values(BLINK_SETTING_META).flatMap(values => values.slice(0, 2)), ...Object.values(BLINK_OPTION_LABELS)];
  for (const label of labels) assert.ok(Object.hasOwn(ADVANCED_COPY, label) || label === "Standard", label);
  assert.equal(booleanStateText(true, "en"), "Enabled");
  assert.match(videoQualityOptions(["best"], "", "en")[0].description, /Highest video quality/);
  assert.equal(videoQualityOptions(["Elimina"], "", "en")[0].label, "Elimina");
  assert.match(recordingStorageSummary({ directory: "/media/Elimina", kind: "media" }, "en"), /^Archive: \/media\/Elimina/);
});

test("only explicit authored nodes are localized; user names and input values stay intact", () => {
  const authored = { textContent: "Salva", getAttribute: () => "Salva" };
  const user = { textContent: "Salva", value: "Elimina" };
  const root = { querySelectorAll: selector => selector === "[data-copy]" ? [authored] : [] };
  assert.equal(localizeCopy(root, "en"), true);
  assert.equal(authored.textContent, "Save");
  assert.deepEqual(user, { textContent: "Salva", value: "Elimina" });
  assert.equal(localizeCopy(root, "en"), false);
  assert.equal(localizeCopy(root, "it"), true);
  assert.equal(authored.textContent, "Salva");
});
