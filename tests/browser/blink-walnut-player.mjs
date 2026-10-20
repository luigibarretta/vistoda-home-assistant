// Operator test: feed a bounded fragmented MP4 fixture on stdin. Kept only in
// RAM, never logged/saved. Loopback-only HTTP, muted browser, no microphone.
import assert from "node:assert/strict";
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { createRequire } from "node:module";
const playwright = createRequire(import.meta.url)("playwright");
const chunks = []; let size = 0;
for await (const chunk of process.stdin) {
  size += chunk.length;
  if (size > 4 * 1024 * 1024) throw new Error("Fixture exceeds RAM budget");
  chunks.push(chunk);
}
const fixture = Buffer.concat(chunks);
assert.ok(fixture.length > 32);
const frontend = new URL("../../custom_components/media_bridge/frontend/", import.meta.url);
const server = createServer(async (request, response) => {
  const name = request.url.slice(1);
  if (name === "fixture.mp4") {
    response.setHeader("Content-Type", "video/mp4"); response.end(fixture); return;
  }
  if (/^[\w-]+\.js$/.test(name)) {
    try { response.setHeader("Content-Type", "text/javascript");
      response.end(await readFile(new URL(name, frontend))); return; }
    catch { response.writeHead(404); response.end(); return; }
  }
  response.setHeader("Content-Type", "text/html");
  response.end('<!doctype html><body><video muted autoplay playsinline></video></body>');
});
await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
const evidence = [];
try {
  for (const engine of ["chromium", "firefox", "webkit"]) {
    const browser = await playwright[engine].launch({ headless: true,
      ...(engine === "chromium" ? { args: ["--no-sandbox", "--mute-audio"] } : {}) });
    try {
      const page = await browser.newPage();
      const mediaMessages = [];
      if (engine === "chromium") {
        const diagnostics = await page.context().newCDPSession(page);
        await diagnostics.send("Media.enable");
        diagnostics.on("Media.playerMessagesLogged", (event) => {
          for (const message of event.messages) if (["error", "warning"].includes(message.level)) {
            mediaMessages.push(message.message.slice(0, 300));
          }
        });
      }
      await page.goto(`http://127.0.0.1:${server.address().port}/`);
      const result = await page.evaluate(async () => {
        const { WalnutPlayer } = await import("/blink-walnut-player.js");
        const video = document.querySelector("video");
        let failure = null; let played = false;
        const player = new WalnutPlayer(video, () => { played = true; }, (error) => { failure ||= error.message; });
        try {
          const bytes = new Uint8Array(await (await fetch("/fixture.mp4")).arrayBuffer());
          // Deliberately split the initialization header across chunks.
          await player.append(bytes.slice(0, 13));
          for (let offset = 13; offset < bytes.length; offset += 32768) {
            await player.append(bytes.slice(offset, offset + 32768));
          }
          const until = performance.now() + 15000;
          while (performance.now() < until && !failure && (!played || video.videoWidth === 0)) {
            await new Promise((resolve) => setTimeout(resolve, 50));
          }
          return { played, width: video.videoWidth, height: video.videoHeight,
            muted: video.muted, failure, ready_state: video.readyState,
            media_error: video.error?.message || null };
        } finally { player.stop(); }
      });
      evidence.push({ engine, ...result, mediaMessages });
    } catch (error) {
      evidence.push({ engine, played: false, failure: error.message.split("\n")[0].slice(0,180) });
    } finally { await browser.close(); }
  }
  console.log(JSON.stringify({ browser_playback: evidence, media_files_written: false }));
  assert.ok(evidence.every((item) => item.played && item.width > 0 && item.muted && !item.failure));
} finally { await new Promise((resolve) => server.close(resolve)); }
