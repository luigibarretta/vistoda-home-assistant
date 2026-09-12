// Browser fullscreen lifecycle, with a synthetic HA shadow-DOM player (no camera).
import assert from "node:assert/strict";
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { createRequire } from "node:module";
const playwright = createRequire(import.meta.url)("playwright");
const frontend = new URL("../../custom_components/media_bridge/frontend/", import.meta.url);
const server = createServer(async (request, response) => {
  if (/^\/[\w-]+\.js$/.test(request.url)) {
    try { response.setHeader("Content-Type", "text/javascript");
      response.end(await readFile(new URL(request.url.slice(1), frontend))); return; }
    catch { response.writeHead(404); response.end(); return; }
  }
  response.end("<!doctype html><body></body>");
});
await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
try {
  for (const engine of process.env.BROWSER_ENGINE ? [process.env.BROWSER_ENGINE] : ["chromium", "firefox", "webkit"]) {
    const browser = await playwright[engine].launch({ headless: true });
    try {
      const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
      await page.goto(`http://127.0.0.1:${server.address().port}/`);
      await page.evaluate(async () => {
        const { LiveFullscreen } = await import("/live-fullscreen.js");
        const host = document.createElement("test-view"); document.body.append(host);
        const root = host.attachShadow({ mode: "open" });
        root.innerHTML = '<div id="stage"><video></video><button>Fullscreen</button></div>';
        const stage = root.querySelector("#stage");
        window.initialVideo = stage.querySelector("video");
        window.fullscreenControl = new LiveFullscreen(stage, (active) => {
          root.querySelector("button").textContent = active ? "Exit fullscreen" : "Fullscreen";
        });
        root.querySelector("button").onclick = () => fullscreenControl.toggle().catch((error) => {
          window.fullscreenError = error.message;
        });
      });
      await page.getByRole("button", { name: "Fullscreen", exact: true }).click();
      await page.waitForFunction(() => fullscreenControl.active || window.fullscreenError);
      assert.equal(await page.evaluate(() => window.fullscreenError), undefined, engine);
      await page.getByRole("button", { name: "Exit fullscreen", exact: true }).click();
      await page.waitForFunction(() => !fullscreenControl.active);
      assert.equal(await page.evaluate(() => initialVideo === fullscreenControl.stage.querySelector("video")), true);
      await page.evaluate(() => fullscreenControl.dispose());
      console.log(`${engine}: fullscreen enter/exit preserves player at mobile viewport`);
    } finally { await browser.close(); }
  }
} finally { await new Promise((resolve) => server.close(resolve)); }
