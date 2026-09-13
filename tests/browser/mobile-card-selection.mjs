// Synthetic gesture test. No Home Assistant or provider mutation.
import assert from "node:assert/strict";
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { createRequire } from "node:module";

const playwright = createRequire(import.meta.url)("playwright");
const frontend = new URL("../../custom_components/media_bridge/frontend/", import.meta.url);
const server = createServer(async (request, response) => {
  if (request.url === "/mobile-card-selection.js") {
    response.setHeader("Content-Type", "text/javascript");
    response.end(await readFile(new URL("mobile-card-selection.js", frontend))); return;
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
        const { MobileCardSelection } = await import("/mobile-card-selection.js");
        const host = document.createElement("section"); host.attachShadow({ mode: "open" });
        host.shadowRoot.innerHTML = `<style>.item{height:80px;margin:8px;border:1px solid}</style>
          ${[1, 2, 3].map((id) => `<article class="item" data-selection-key="${id}">Clip ${id}</article>`).join("")}`;
        document.body.append(host); window.selected = new Set(); window.renders = 0;
        window.selection = new MobileCardSelection(host.shadowRoot, ".item", {
          selected: (key) => selected.has(key),
          select: (key, value) => { value ? selected.add(key) : selected.delete(key); },
          render: () => { renders += 1; },
        });
      });
      const rows = page.locator("section .item");
      const first = await rows.nth(0).boundingBox();
      const second = await rows.nth(1).boundingBox();
      const third = await rows.nth(2).boundingBox();
      await page.mouse.move(first.x + 20, first.y + 20); await page.mouse.down();
      await page.waitForTimeout(470);
      await page.mouse.move(second.x + 20, second.y + 20, { steps: 3 });
      await page.mouse.move(third.x + 20, third.y + 20, { steps: 3 }); await page.mouse.up();
      assert.deepEqual(await page.evaluate(() => [...selected]), ["1", "2", "3"]);
      await rows.nth(1).click();
      assert.deepEqual(await page.evaluate(() => [...selected]), ["1", "3"]);
      await page.evaluate(() => { selection.setMode(false); selected.clear(); });
      await page.mouse.move(first.x + 20, first.y + 20); await page.mouse.down();
      await page.mouse.move(first.x + 20, first.y + 50); await page.waitForTimeout(470); await page.mouse.up();
      assert.deepEqual(await page.evaluate(() => [...selected]), [], "ordinary vertical scroll must not select");
      await page.close();
      console.log(`${engine}: long-press, drag-select, tap-toggle and scroll cancellation`);
    } finally { await browser.close(); }
  }
} finally { await new Promise((resolve) => server.close(resolve)); }
