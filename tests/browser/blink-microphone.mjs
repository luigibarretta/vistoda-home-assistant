// Synthetic capture only: no physical microphone, camera, or audio files.
import assert from "node:assert/strict";
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { createRequire } from "node:module";
import { virtualAudio } from "./virtual-audio.mjs";
const playwright = createRequire(import.meta.url)("playwright");
const frontend = new URL("../../custom_components/media_bridge/frontend/", import.meta.url);
const server = createServer(async (request, response) => {
  if (/^\/[\w-]+\.js$/.test(request.url)) {
    try { response.setHeader("Content-Type", "text/javascript");
      response.end(await readFile(new URL(request.url.slice(1), frontend))); return; }
    catch { response.writeHead(404); response.end(); return; }
  }
  response.end('<!doctype html><button id="start">Test capture</button>');
});
await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
let audio;
try {
  audio = await virtualAudio();
  for (const engine of process.env.BROWSER_ENGINE ? [process.env.BROWSER_ENGINE] : ["chromium", "firefox", "webkit"]) {
    const browser = await playwright[engine].launch({ headless: true, env: { ...process.env, ...audio.env } });
    try {
      const page = await browser.newPage();
      await page.goto(`http://127.0.0.1:${server.address().port}/`);
      await page.evaluate(async () => {
        const { WalnutMicrophone } = await import("/blink-walnut-microphone.js");
        document.querySelector("button").onclick = async () => {
          let source; let microphone;
          try {
            const Context = globalThis.AudioContext || globalThis.webkitAudioContext;
            source = new Context(); window.step = "source-resume"; await source.resume();
            const destination = source.createMediaStreamDestination();
            const oscillator = source.createOscillator(); oscillator.frequency.value = 440;
            oscillator.connect(destination); oscillator.start();
            navigator.mediaDevices.getUserMedia = async () => destination.stream;
            const frames = []; const errors = [];
            microphone = new WalnutMicrophone({ hass: { locale: { language: "en" } } },
              async (frame) => frames.push(frame), (error) => errors.push(error.message));
            window.step = "capture-prepare"; await microphone.prepare(); microphone.enable();
            const deadline = Date.now() + 4500;
            while (frames.length < 10 && !errors.length && Date.now() < deadline) {
              await new Promise((resolve) => setTimeout(resolve, 25));
            }
            const clock = microphone.context.currentTime;
            microphone.stop(); const count = frames.length;
            await new Promise((resolve) => setTimeout(resolve, 100));
            window.result = { count, clock, sizes: [...new Set(frames.map((frame) => atob(frame).length))],
              stopped: frames.length === count && microphone.context.state === "closed",
              tracksEnded: destination.stream.getTracks().every((track) => track.readyState === "ended"), errors };
            oscillator.stop();
          } catch (error) { window.result = { failure: error.message }; }
          finally { microphone?.stop(); await source?.close(); }
        };
      });
      await page.getByRole("button").click();
      await page.waitForFunction(() => window.result, null, { timeout: 10000 }).catch(async (error) => {
        console.log(JSON.stringify({ engine, step: await page.evaluate(() => window.step) })); throw error;
      });
      const result = await page.evaluate(() => window.result);
      assert.equal(result.failure, undefined, JSON.stringify({ engine, result }));
      assert.ok(result.count >= 8 && result.count <= 24, JSON.stringify({ engine, result }));
      assert.deepEqual(result.sizes, [1024]); assert.deepEqual(result.errors, []);
      assert.equal(result.stopped, true); assert.equal(result.tracksEnded, true);
      console.log(`${engine}: PCM32ms capture, exact frames and teardown passed`);
    } finally { await browser.close(); }
  }
} finally { await audio?.stop(); await new Promise((resolve) => server.close(resolve)); }
