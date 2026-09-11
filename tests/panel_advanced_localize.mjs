import assert from "node:assert/strict";
import test from "node:test";
import { ADVANCED_COPY, copy, localizeCopy } from "../custom_components/media_bridge/frontend/panel-copy.js";

test("advanced EN/IT copy preserves every interpolation contract", () => {
  const parameters = (message) => [...message.matchAll(/\{(p\d+)\}/g)].map((match) => match[1]).sort();
  assert.ok(Object.keys(ADVANCED_COPY).length > 300);
  for (const [italian, english] of Object.entries(ADVANCED_COPY)) {
    assert.equal(typeof english, "string");
    assert.ok(english.trim(), italian);
    assert.deepEqual(parameters(italian), parameters(english), italian);
    assert.equal(copy("it-IT", italian), italian);
    assert.equal(copy("en-GB", italian), english);
  }
});

test("advanced locale follows HA context and never translates interpolated user values", () => {
  const name = "Apri portone <private> & {p9}";
  assert.equal(copy({ host: { _hass: { locale: { language: "en" } } } }, "Aprire l’ingresso {p0}?", { p0: name }),
    `Unlock the entrance ${name}?`);
  assert.equal(copy({ hass: { language: "it" } }, "Apri portone"), "Apri portone");
  assert.equal(copy("fr", "Apri portone"), "Unlock entrance");
  assert.equal(copy("en", "arbitrary device or upstream message"), "arbitrary device or upstream message");
});

test("explicit static markers localize text and accessibility without touching user content", () => {
  const text = { textContent: "Apri portone", getAttribute: () => "Apri portone" };
  const title = { attributes: {}, getAttribute: () => "Copia percorso archivio locale",
    setAttribute(key, value) { this.attributes[key] = value; } };
  const untouchedUserNode = { textContent: "Apri portone", value: "Apri portone" };
  const root = { querySelectorAll(selector) {
    return selector === "[data-copy]" ? [text] : selector === "[data-copy-title]" ? [title] : [];
  } };
  localizeCopy(root, "en");
  assert.equal(text.textContent, "Unlock entrance");
  assert.equal(title.attributes.title, "Copy local archive path");
  assert.deepEqual(untouchedUserNode, { textContent: "Apri portone", value: "Apri portone" });
  localizeCopy(root, "it");
  assert.equal(text.textContent, "Apri portone");
});
