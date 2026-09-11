// Run with NODE_PATH pointing to a Playwright installation. All HA traffic is synthetic.
import assert from "node:assert/strict";
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { createRequire } from "node:module";
import { checkAdvancedPanel, checkAuthoredCopy } from "./panel-localization.mjs";
const { chromium } = createRequire(import.meta.url)("playwright");
const frontend = new URL("../../custom_components/media_bridge/frontend/", import.meta.url);
const server = createServer(async (request, response) => {
  const filename = request.url?.split("?")[0].slice(1);
  if (filename && /^[\w-]+\.js$/.test(filename)) {
    try {
      response.setHeader("Content-Type", "text/javascript");
      response.end(await readFile(new URL(filename, frontend))); return;
    } catch { response.writeHead(404); response.end(); return; }
  }
  response.setHeader("Content-Type", "text/html");
  response.end(`<!doctype html><html><head><style>
    body{margin:0;font:16px Arial;--primary-text-color:#eee;--secondary-text-color:#aaa;
    --primary-color:#8974ff;--divider-color:#555;--card-background-color:#252525;
    --secondary-background-color:#343434;background:#151515;color:#eee}
    #shell{display:flex;width:100%;min-height:100vh}#shell>aside{width:64px;flex:0 0 64px}
    #shell>main{flex:1;min-width:0}ha-icon{display:inline-block;width:24px;height:24px}
    @media(max-width:600px){#shell>aside{display:none}}
    </style></head><body><div id="shell"><aside></aside><main></main></div></body></html>`);
});
await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
const browser = await chromium.launch({ headless: true, args: ["--no-sandbox"] });
const origin = `http://127.0.0.1:${server.address().port}`;
const errors = [];
try {
  let page;
  for (const language of ["en", "it"]) for (const width of [320, 360, 393, 600, 768, 1280]) {
    for (const provider of ["overview", "ring", "blink", "ezviz"]) {
      await page?.close();
      page = await browser.newPage({ viewport: { width, height: 900 } });
      page.on("pageerror", (error) => errors.push(error.message));
      await page.goto(`${origin}/vistoda/${provider === "overview" ? "" : provider}`);
      await page.addScriptTag({ type: "module", url: `${origin}/vistoda-panel.js` });
      await page.waitForFunction(() => customElements.get("vistoda-panel"));
      await page.evaluate(({ provider, language }) => {
        const entries = ["north", "south"].map((side) => ({
          entry_id: side, name: "Vistoda · Entrance", device_name: "Shared entrance name",
          location_name: `${side} building with a long address`, city: "Town", available: true,
          controls: { open_door: `button.${side}` },
          identity_configuration: { selection: { device_name: "ring", location_name: "ring", city: "custom" },
            custom: { city: "Elimina" }, available: { ring: { device_name: "Elimina", location_name: "Salva" } } },
        }));
        const cameras = Array.from({ length: 5 }, (_, index) => ({
          name: `Camera ${index} with a very long descriptive name`,
          entities: { camera: [{ entity_id: `camera.test${index}`,
            config_entry_id: `ezviz-${index}` }] },
        }));
        window.requests = []; window.inventoryFailure = false;
        window.hassFixture = {
          locale: { language }, user: { is_admin: true }, config: { time_zone: "Europe/Rome" },
          states: Object.fromEntries(cameras.map((_, index) => [`camera.test${index}`, {
            state: "idle", attributes: { alias: index < 2 ? "shared-alias" : `camera${index}`,
              entry_id: `ezviz-${index}`, network_id: index < 3 ? 1 : 2,
              snapshot_updated_at: "2026-09-11T10:00:00Z" },
          }])),
          hassUrl: (path) => path,
          callService: () => { throw new Error("No service calls are allowed in browser acceptance"); },
          callWS: async (request) => {
            window.requests.push(request);
            if (request.type === "media_bridge/panel/info") {
              if (window.inventoryFailure) throw new Error("offline");
              return { providers: Object.fromEntries(["ring", "blink", "ezviz"].map((key) => [key, {
                configured: true, available: true, devices: key === "ring" ? [] : cameras,
                entries: key === "ezviz" ? cameras.map((_, index) => ({
                  entry_id: `ezviz-${index}`, alias: index < 2 ? "shared-alias" : `camera${index}`,
                  available: index !== 4,
                })) : [{ entry_id: key, alias: "camera0", available: true }],
                counts: { camera: 5 },
              }])) };
            }
            if (request.type === "media_bridge/ring/info") return { entries };
            if (request.type === "media_bridge/ring/history") return {
              identity: entries.find((entry) => entry.entry_id === request.entry_id),
              events: [{ event_id: request.entry_id, occurred_at: 1789120800, event_type: "ding" }], next_cursor: null,
            };
            if (request.type === "blink_live_bridge/camera/settings") return { name: "Elimina",
              settings: [{ key: "motion_detection", kind: "boolean", value: true, writable: true },
                { key: "video_quality", kind: "select", value: "best", options: ["saver", "standard", "best"], writable: true },
                { key: "camera_name", kind: "text", value: "Elimina", writable: true }], revision: "fake" };
            if (request.type === "blink_live_bridge/camera/zones") return { activity_masks: Array(25).fill(4095),
              privacy_zones: [], privacy_supported: true, revision: "fake" };
            if (request.type === "media_bridge/ezviz/snapshot/refresh") return {
              updated_at: "2026-09-11T12:00:00Z",
            };
            const lists = [{ list_id: "fixture", name: "Elimina", recording_ids: [] }];
            if (request.type === "media_bridge/ring/recordings/list") return { lists, recordings: [
              { recording_id: "r1", started_at: 1789120800, ended_at: 1789120860, bytes: 1024,
                storage_path: "/media/Elimina/call.webm" }], storage: { directory: "/media/Elimina", kind: "media" } };
            if (request.type === "blink_live_bridge/local_storage/list") return { storages: [{ network_name: "Elimina",
              network_id: 1, sync_module_id: 2, manifest_id: 3, status: { can_format_usb: true, can_delete_clips: true },
              clips: [{ id: 4, device_name: "Elimina", created_at: 1789120800000, media_available: true }],
              pagination: { page: 1, total_pages: 1, total_items: 1 } }] };
            if (/\/recordings\/list$/.test(request.type)) {
              const index = Number(String(request.entry_id || "").replace("ezviz-", ""));
              const cameraAlias = request.alias || (Number.isInteger(index)
                ? (index < 2 ? "shared-alias" : `camera${index}`) : "camera0");
              return { recordings: [{ recording_id: "p1", camera: cameraAlias,
              requested_at: "2026-09-11T10:00:00Z", status: "ready", requested_duration_seconds: 15 }],
              pagination: { page: 1, total_pages: 1, total_items: 1 }, storage: { directory: "/data/Elimina" } };
            }
            if (/\/(list|storage)$/.test(request.type)) return { recordings: [], lists, storages: [] };
            throw new Error(`Unexpected WS action: ${request.type}`);
          },
        };
        const panel = document.createElement("vistoda-panel");
        panel.panel = { config: { provider } }; panel.hass = window.hassFixture;
        document.querySelector("main").append(panel);
      }, { provider, language });
      await page.waitForFunction(() => document.querySelector("vistoda-panel")?._info);
      const check = async (label) => {
        const metrics = await page.evaluate(() => {
          const violations = [];
          const visit = (root) => {
            for (const element of root.querySelectorAll("*")) {
              const rect = element.getBoundingClientRect();
              if (rect.width && rect.height && element.checkVisibility() &&
                  element.matches('button, a, select, input[type="range"]') &&
                  (rect.width < 43.9 || rect.height < 43.9)) {
                violations.push(`${element.localName}#${element.id}: ${rect.width}x${rect.height}`);
              }
              if (element.shadowRoot) visit(element.shadowRoot);
            }
          }; visit(document);
          return { width: document.documentElement.scrollWidth, viewport: innerWidth, violations };
        });
        assert.ok(metrics.width <= metrics.viewport, `${label}: overflow ${JSON.stringify(metrics)}`);
        assert.deepEqual(metrics.violations, [], `${label}: undersized targets`);
      };
      await check(`${provider}@${width}`);
      await checkAuthoredCopy(page, language);
      await checkAdvancedPanel(page, provider, language, check);
      assert.equal(await page.locator(`vistoda-panel nav a[data-provider="${provider}"]`).getAttribute("aria-current"), "page");
      if (provider === "ring") {
        const devices = page.locator("vistoda-ring-view .device-card");
        assert.equal(await devices.count(), 2);
        await devices.filter({ hasText: "south building" }).click();
        assert.equal(await devices.filter({ hasText: "south building" }).getAttribute("aria-selected"), "true");
        await page.locator("vistoda-ring-view #history-open").click();
        await page.waitForFunction(() => window.requests.some((request) => request.type === "media_bridge/ring/history"));
        assert.equal(await page.locator("vistoda-ring-history #device-filter").textContent(), "Shared entrance name");
        assert.match(await page.locator("vistoda-ring-history #location").textContent(), /south/);
        await check(`history@${width}`);
      }
      if (provider === "blink") {
        assert.equal(await page.locator("vistoda-blink-view .dot").count(), 5);
        const dot = await page.locator("vistoda-blink-view .dot").first().evaluate((element) => {
          const style = getComputedStyle(element, "::before"); return [style.width, style.height];
        });
        assert.deepEqual(dot, ["8px", "8px"]);
      }
      if (provider === "ezviz") {
        assert.equal(await page.locator("vistoda-ezviz-view .dot").count(), 5);
        const cameraPrevious = page.locator("vistoda-ezviz-view nav.pager > #previous");
        assert.equal(await cameraPrevious.getAttribute("title"), null);
        await page.locator("vistoda-ezviz-view .dot").nth(1).click();
        assert.match(await page.locator("vistoda-ezviz-view #camera-name").textContent(), /Camera 1/);
        const snapshotRequests = await page.evaluate(() => window.requests.filter(
          (request) => request.type.includes("snapshot/refresh")));
        assert.deepEqual(snapshotRequests, [], "opening and selecting cameras must remain passive");
        await page.locator("vistoda-ezviz-view #refresh").click();
        await page.waitForFunction(() => window.requests.some(
          (request) => request.type === "media_bridge/ezviz/snapshot/refresh"));
        const refreshEntry = await page.evaluate(() => window.requests.findLast(
          (request) => request.type === "media_bridge/ezviz/snapshot/refresh").entry_id);
        assert.equal(refreshEntry, "ezviz-1", "duplicate aliases must use the exact camera entry");
        await page.locator("vistoda-ezviz-view .dot").first().click();
        await cameraPrevious.click();
        assert.match(await page.locator("vistoda-ezviz-view #camera-name").textContent(), /Camera 4/,
          "previous from the first camera must wrap to the last camera");
        await page.evaluate(() => {
          const view = document.querySelector("vistoda-panel")._child;
          view._cameraIndex = 0;
          view._selectedCameraId = "camera.test0";
          view._render();
          view._startSwipe({ isPrimary: true, pointerId: 7, clientX: 100, clientY: 100 });
          view._finishSwipe({ pointerId: 7, clientX: 102, clientY: 180 });
        });
        assert.match(await page.locator("vistoda-ezviz-view #camera-name").textContent(), /Camera 0/,
          "vertical movement must not page cameras");
      }
      await page.evaluate(() => { window.inventoryFailure = true; });
      await page.getByRole("button", { name: language === "en" ? "Refresh devices and status" : "Aggiorna dispositivi e stato", exact: true }).click();
      await page.waitForFunction(() => document.querySelector("vistoda-panel")._info.error);
      assert.match(await page.locator("#inventory-status").textContent(), /Unable to load devices|Impossibile caricare i dispositivi/);
      assert.equal(await page.locator("vistoda-panel > main > #content").isVisible(), false);
      await page.evaluate(() => { window.inventoryFailure = false; });
      await page.getByRole("button", { name: language === "en" ? "Refresh devices and status" : "Aggiorna dispositivi e stato", exact: true }).click();
      await page.waitForFunction(() => !document.querySelector("vistoda-panel")._info.error);
      assert.equal(await page.locator("vistoda-panel > main > #content").isVisible(), true);
      console.log(`PASS ${language} ${provider} ${width}px: width, targets, advanced copy, active tab, recovery`);
    }
  }
  await page.evaluate(async () => {
    const view = document.querySelector("vistoda-panel")._child;
    view.info = { providers: { ezviz: { configured: false, entries: [], devices: [] } } };
  });
  assert.equal(await page.getByRole("link", { name: "Configura EZVIZ", exact: true }).isVisible(), true);
  assert.deepEqual(errors, [], "browser console errors");
} finally {
  await browser.close(); server.close();
}
