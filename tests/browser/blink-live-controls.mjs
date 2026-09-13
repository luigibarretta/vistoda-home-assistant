// Synthetic provider/session only. No camera, user microphone or HA mutation.
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
  response.end('<!doctype html><body style="margin:0"></body>');
});
await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
try {
  for (const engine of ["chromium", "firefox", "webkit"]) {
    const browser = await playwright[engine].launch({ headless: true });
    try {
      for (const width of [390, 1280]) {
        const page = await browser.newPage({ viewport: { width, height: 844 } });
        await page.goto(`http://127.0.0.1:${server.address().port}/`);
        await page.evaluate(async () => {
          await import("/blink-view.js");
          const { BlinkLiveSession } = await import("/blink-live-session.js");
          window.actions = [];
          BlinkLiveSession.prototype.start = async function () {
            actions.push("live"); this.mode = "legacy";
            this.onState({ phase: "active", transport: "walnut", microphoneSupported: true,
              sessionTiming: { continue_interval: 30, continue_warning: 10, duration: 75, remaining_ms: 75000 } });
          };
          BlinkLiveSession.prototype.setMicrophone = function (enabled) { actions.push(enabled ? "talk" : "release"); };
          window.view = document.createElement("vistoda-blink-view"); document.body.append(view);
          view.hass = { locale: { language: "en" }, user: { is_admin: true }, states: {
            "camera.test": { state: "idle", attributes: { alias: "test" } },
          }, hassUrl: (path) => path,
          callWS: async (request) => {
            if (request.type === "call_service") actions.push("snapshot");
            return { recordings: [], lists: [], storages: [] };
          },
          callService: async () => { actions.push("snapshot"); },
          };
          view.info = { providers: { blink: { available: true, entries: [{ entry_id: "test" }],
            devices: [{ name: "Test camera", entities: { camera: [{ entity_id: "camera.test" }] } }] } } };
        });
        const stage = page.locator("#stage");
        assert.equal(await page.locator("#system #provider-head").count(), 1);
        assert.equal(await stage.locator("#live").count(), 1);
        assert.equal(await page.locator("#recording-section").evaluate((node) => node.open), false);
        await stage.locator("#live").click();
        await page.waitForFunction(() => actions.includes("live"));
        assert.deepEqual(await page.evaluate(() => actions.slice(0, 2)), ["snapshot", "live"]);
        assert.equal(await page.locator("#mobile-live-dialog").evaluate((node) => node.open), width < 768);
        if (width < 768) {
          const box = await stage.boundingBox();
          assert.ok(box.width >= 389 && box.height >= 843, JSON.stringify(box));
        }
        const mic = stage.locator("#microphone");
        const micBox = await mic.boundingBox();
        assert.ok(micBox.width >= 100 && micBox.height >= 44 && micBox.height <= 64, JSON.stringify(micBox));
        await stage.locator("#rotate").click();
        assert.equal(await stage.locator("#rotate").getAttribute("aria-pressed"), "true");
        assert.match(await stage.locator("#legacy-live").getAttribute("style"), /rotate\(90deg\)/);
        await stage.locator("#rotate").click();
        assert.equal(await stage.locator("#rotate").getAttribute("aria-pressed"), "false");
        assert.equal(await stage.locator("#live-loader").isVisible(), true);
        assert.equal(await stage.locator("#talk-status").isVisible(), true);
        await mic.focus(); await page.keyboard.down("Space"); await page.keyboard.up("Space");
        assert.deepEqual(await page.evaluate(() => actions.slice(-2)), ["talk", "release"]);
        await page.evaluate(() => {
          view._liveControls.promptDeadline = performance.now() + 1000;
          view._liveControls.tick();
        });
        await stage.locator("#continue").click();
        assert.ok(await page.evaluate(() => view._liveControls.promptDeadline - performance.now() > 28000));
        if (width < 768) await page.keyboard.press("Escape");
        else await stage.locator("#live").click();
        await page.waitForFunction(() => view._liveSession === null);
        assert.equal(await page.locator("#mobile-live-dialog").evaluate((node) => node.open), false);
        assert.equal(await page.locator("#gallery #stage").count(), 1);
        await page.evaluate(() => {
          view._hass.callWS = async (request) => {
            if (request.type === "call_service") throw new Error("provider HTTP 502");
            return { recordings: [], lists: [], storages: [] };
          };
        });
        await stage.locator("#live").click();
        await page.waitForFunction(() => view._liveState.phase === "active");
        assert.match(await stage.locator("#live-message").textContent(), /Snapshot not updated/);
        assert.doesNotMatch(await stage.locator("#live-message").textContent(), /502/);
        await page.evaluate(() => view._liveControls.close());
        const sharedViewer = await page.evaluate(async () => {
          const { CameraLiveDialog } = await import("/camera-live-dialog.js");
          const host = document.createElement("div"); host.attachShadow({ mode:"open" }); document.body.append(host);
          const requested = [];
          window.loadCardHelpers = async () => ({ createCardElement: async config => {
            requested.push(config.entity); const card = document.createElement("div");
            card.append(document.createElement("video")); return card;
          } });
          const viewer = new CameraLiveDialog(host);
          await viewer.open({ states:{ "camera.ezviz": { attributes:{} } }, locale:{language:"en"} }, "camera.ezviz");
          const dialog = viewer.dialog; const root = dialog.firstElementChild.shadowRoot;
          root.getElementById("rotate").click();
          const rotated = root.getElementById("rotate").getAttribute("aria-pressed") === "true";
          root.getElementById("close").click();
          const closed = !dialog.isConnected && viewer.timer === null;
          await viewer.open({ states:{ "camera.ring": { attributes:{} } }, locale:{language:"en"} }, "camera.ring");
          viewer.close(); host.remove();
          return { requested, rotated, closed };
        });
        assert.deepEqual(sharedViewer.requested, ["camera.ezviz", "camera.ring"]);
        assert.equal(sharedViewer.rotated, true); assert.equal(sharedViewer.closed, true);
        const alarm = await page.evaluate(async () => {
          const control = document.createElement("vistoda-system-arm-control"); document.body.append(control);
          const calls = []; const toasts = [];
          const hass = { locale: { language: "en" }, states: {
            "alarm_control_panel.fixture": { state: "disarmed", attributes: { supported_features: 2 } },
          }, callService: async (...args) => calls.push(args) };
          control.addEventListener("hass-notification", (event) => toasts.push(event.detail.message));
          control.configure(hass, "alarm_control_panel.fixture", "Fixture system");
          const before = control.$("toggle").textContent;
          await control.toggle();
          const pending = control.$("toggle").disabled && toasts.length === 0 && control.$("toggle").textContent === before;
          hass.states["alarm_control_panel.fixture"].state = "armed_away";
          control.configure(hass, "alarm_control_panel.fixture", "Fixture system");
          const after = control.$("toggle").textContent;
          const confirmed = toasts.length === 1 && !control.$("toggle").disabled;
          hass.states["alarm_control_panel.fixture"].state = "unavailable"; control.render();
          const unavailable = control.$("toggle").disabled;
          control.remove(); return { before, after, pending, confirmed, unavailable, calls };
        });
        assert.match(alarm.before, /Arm/); assert.match(alarm.after, /Disarm/);
        assert.equal(alarm.pending, true); assert.equal(alarm.confirmed, true); assert.equal(alarm.unavailable, true);
        assert.equal(alarm.calls.length, 1);
        await page.close();
        console.log(`${engine} ${width}px: snapshot before live, overlay controls, PTT, Continue, close teardown`);
      }
    } finally { await browser.close(); }
  }
} finally { await new Promise((resolve) => server.close(resolve)); }
