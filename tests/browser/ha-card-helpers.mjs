// Cold-entry DOM test: HA's registered loader is simulated; no camera is opened.
import assert from "node:assert/strict";
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { createRequire } from "node:module";
const playwright = createRequire(import.meta.url)("playwright");
const frontend = new URL("../../custom_components/media_bridge/frontend/", import.meta.url);
const server = createServer(async (request, response) => {
  const name = request.url.slice(1);
  if (/^[\w-]+\.js$/.test(name)) {
    try { response.setHeader("Content-Type", "text/javascript");
      response.end(await readFile(new URL(name, frontend))); return; }
    catch { response.writeHead(404); response.end(); return; }
  }
  response.setHeader("Content-Type", "text/html"); response.end("<!doctype html><body></body>");
});
await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
const engine = process.env.BROWSER_ENGINE || "chromium";
const browser = await playwright[engine].launch({ headless: true,
  ...(engine === "chromium" ? { args: ["--no-sandbox"] } : {}) });
try {
  const page = await browser.newPage();
  const errors = []; page.on("pageerror", (error) => errors.push(error.message));
  await page.goto(`http://127.0.0.1:${server.address().port}/`);
  const result = await page.evaluate(async () => {
    const { BlinkLegacyLiveSession } = await import("/blink-legacy-live-session.js");
    const resolver = document.createElement("partial-panel-resolver");
    const panel = document.createElement("vistoda-test-panel");
    const root = panel.attachShadow({ mode: "open" });
    const host = document.createElement("div"); root.append(host); resolver.append(panel);
    document.body.append(resolver);
    const originalUrl = location.href;
    let loaded = 0; let configured;
    resolver.routerOptions = { routes: { casa: { tag: "ha-panel-lovelace", load: async () => {
      loaded++;
      globalThis.loadCardHelpers = async () => ({ createCardElement: async (configuration) => {
        configured = configuration;
        return document.createElement("hui-picture-entity-card");
      } });
    } } } };
    const initiallyMissing = typeof globalThis.loadCardHelpers !== "function";
    const session = new BlinkLegacyLiveSession({ locale: { language: "en" } }, host);
    await session.start("camera.synthetic");
    const mounted = host.firstElementChild?.localName;
    session.stop();
    return { initiallyMissing, loaded, configured, mounted,
      unchangedUrl: originalUrl === location.href, closed: !host.childElementCount && host.hidden };
  });
  assert.equal(result.initiallyMissing, true); assert.equal(result.loaded, 1);
  assert.equal(result.mounted, "hui-picture-entity-card");
  assert.equal(result.configured.camera_view, "live"); assert.equal(result.closed, true);
  assert.equal(result.unchangedUrl, true); assert.deepEqual(errors, []);
  console.log(`${engine}: cold custom-panel player bootstrap passed (synthetic HA loader)`);
} finally { await browser.close(); await new Promise((resolve) => server.close(resolve)); }
