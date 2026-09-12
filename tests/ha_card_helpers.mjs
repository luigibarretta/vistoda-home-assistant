import assert from "node:assert/strict";
import test from "node:test";
import { loadHaCardHelpers } from "../custom_components/media_bridge/frontend/ha-card-helpers.js";
import { BlinkLegacyLiveSession } from "../custom_components/media_bridge/frontend/blink-legacy-live-session.js";

test("cold custom-panel entry loads the registered Lovelace module without navigation", async () => {
  let loads = 0;
  const helpers = { createCardElement() {} };
  const resolver = { localName: "partial-panel-resolver", routerOptions: { routes: {
    casa: { tag: "ha-panel-lovelace", load: async () => {
      loads++; globalThis.loadCardHelpers = async () => helpers;
    } },
  } } };
  const host = { parentNode: { host: { parentNode: resolver } } };
  delete globalThis.loadCardHelpers;
  try {
    const [first, second] = await Promise.all([loadHaCardHelpers(host), loadHaCardHelpers(host)]);
    assert.equal(first, helpers); assert.equal(second, helpers); assert.equal(loads, 1);
  } finally { delete globalThis.loadCardHelpers; }
});

test("warm dashboard entry keeps the existing helper without loading routes", async () => {
  const helpers = {};
  globalThis.loadCardHelpers = async () => helpers;
  try { assert.equal(await loadHaCardHelpers({}), helpers); }
  finally { delete globalThis.loadCardHelpers; }
});

test("failed module loading can retry and does not cache a rejection", async () => {
  let attempts = 0;
  const helpers = {};
  const host = { localName: "partial-panel-resolver", routerOptions: { routes: {
    home: { tag: "ha-panel-lovelace", load: async () => {
      if (++attempts === 1) throw new Error("offline");
      globalThis.loadCardHelpers = async () => helpers;
    } },
  } } };
  delete globalThis.loadCardHelpers;
  try {
    await assert.rejects(loadHaCardHelpers(host), /offline/);
    assert.equal(await loadHaCardHelpers(host), helpers);
  } finally { delete globalThis.loadCardHelpers; }
});

test("closing live during lazy load never creates a camera card or starts a stream", async () => {
  let release; let created = 0;
  const helpers = { createCardElement() { created++; } };
  const resolver = { localName: "partial-panel-resolver", routerOptions: { routes: {
    home: { tag: "ha-panel-lovelace", load: () => new Promise((resolve) => {
      release = () => { globalThis.loadCardHelpers = async () => helpers; resolve(); };
    }) },
  } } };
  const host = { parentNode: resolver, replaceChildren() {} };
  delete globalThis.loadCardHelpers;
  try {
    const session = new BlinkLegacyLiveSession({}, host);
    const start = session.start("camera.kitchen");
    session.stop(); release(); await start;
    assert.equal(created, 0); assert.equal(host.hidden, true);
  } finally { delete globalThis.loadCardHelpers; }
});
