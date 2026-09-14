import assert from "node:assert/strict";
import test from "node:test";
import { localizeCopy } from "../custom_components/media_bridge/frontend/panel-copy.js";

test("background state updates leave native select options untouched", () => {
  let text = "Save", mutations = 0;
  const option = {
    get textContent() { return text; },
    set textContent(value) { text = value; mutations++; },
    getAttribute() { return "Salva"; },
  };
  const root = { querySelectorAll: (selector) => selector === "[data-copy]" ? [option] : [] };
  for (let update = 0; update < 100; update++) localizeCopy(root, "en");
  assert.equal(mutations, 0);
  localizeCopy(root, "it");
  assert.equal(text, "Salva");
  assert.equal(mutations, 1);
});
