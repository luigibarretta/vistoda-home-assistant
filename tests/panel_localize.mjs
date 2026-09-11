import assert from "node:assert/strict";
import test from "node:test";
import { localize, panelLanguage, PANEL_MESSAGES } from "../custom_components/media_bridge/frontend/panel-localize.js";

test("panel catalogs have identical keys and interpolation contracts", () => {
  assert.deepEqual(Object.keys(PANEL_MESSAGES.it).sort(), Object.keys(PANEL_MESSAGES.en).sort());
  for (const key of Object.keys(PANEL_MESSAGES.en)) {
    const parameters = (message) => [...message.matchAll(/\{(\w+)\}/g)].map((match) => match[1]).sort();
    assert.deepEqual(parameters(PANEL_MESSAGES.it[key]), parameters(PANEL_MESSAGES.en[key]), key);
  }
});

test("locale fallback and interpolation preserve user content", () => {
  assert.equal(panelLanguage({ locale: { language: "it-CH" } }), "it");
  assert.equal(panelLanguage({ language: "de-DE" }), "en");
  assert.equal(localize("en", "openProvider", { provider: "My <camera>" }), "Open My <camera>");
  assert.equal(localize("it", "openProvider", { provider: "Ring" }), "Apri Ring");
  assert.throws(() => localize("en", "missingKey"), /Unknown Vistoda message/);
});
