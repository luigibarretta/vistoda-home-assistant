import assert from "node:assert/strict";
import test from "node:test";

import {
  booleanStateText,
  videoQualityOptions,
} from "../custom_components/media_bridge/frontend/blink-setting-model.js";

test("boolean camera settings are rendered as current states", () => {
  assert.equal(booleanStateText(true), "Attivata");
  assert.equal(booleanStateText(false), "Disattivata");
});

test("video qualities use the Blink order, recommendation and bandwidth copy", () => {
  const options = videoQualityOptions(["saver", "standard", "best"], "standard");
  assert.deepEqual(options.map(({ value }) => value), ["best", "standard", "saver"]);
  assert.equal(options[1].label, "Standard (consigliata)");
  assert.match(options[0].description, /almeno 3 Mbps/);
  assert.match(options[1].description, /almeno 2 Mbps/);
  assert.match(options[2].description, /almeno 500 Kbps/);
});

test("the provider current value remains visible when support metadata is incomplete", () => {
  const options = videoQualityOptions([], "standard");
  assert.deepEqual(options.map(({ value }) => value), ["standard"]);
});
