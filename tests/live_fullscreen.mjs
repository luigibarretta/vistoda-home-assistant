import test from "node:test";
import assert from "node:assert/strict";
import { LiveFullscreen, findLiveVideo } from "../custom_components/media_bridge/frontend/live-fullscreen.js";

function fixture() {
  const document = new EventTarget();
  const root = {};
  const stage = { ownerDocument: document, getRootNode: () => root, children: [] };
  const updates = [];
  const control = new LiveFullscreen(stage, (active) => updates.push(active));
  return { document, root, stage, control, updates };
}

test("fullscreen preserves the stage and follows Escape inside shadow DOM", async () => {
  const { document, root, stage, control, updates } = fixture();
  let enters = 0;
  stage.requestFullscreen = async () => { enters++; root.fullscreenElement = stage; };
  document.exitFullscreen = async () => { root.fullscreenElement = null; };
  await control.toggle(); assert.equal(control.active, true); assert.equal(enters, 1);
  await control.toggle(); assert.equal(control.active, false);
  document.dispatchEvent(new Event("fullscreenchange")); assert.equal(updates.at(-1), false);
  control.dispose(); const count = updates.length;
  document.dispatchEvent(new Event("fullscreenchange")); assert.equal(updates.length, count);
});

test("iOS fallback finds the visible HA video through nested shadow roots", async () => {
  const { stage, control } = fixture(); let enters = 0; let exits = 0;
  const video = { localName: "video", webkitDisplayingFullscreen: true,
    webkitEnterFullscreen() { enters++; }, webkitExitFullscreen() { exits++; } };
  stage.children = [{ localName: "video", hidden: true },
    { shadowRoot: { children: [{ shadowRoot: { children: [video] } }] } }];
  assert.equal(findLiveVideo(stage), video);
  await control.toggle(); assert.equal(enters, 1);
  await control.exit(); assert.equal(exits, 1); control.dispose();
});

test("denied or unavailable fullscreen fails without replacing the player", async () => {
  const { stage, control } = fixture(); const children = stage.children;
  await assert.rejects(control.toggle(), /fullscreen_unavailable/);
  stage.requestFullscreen = async () => { throw new Error("denied"); };
  await assert.rejects(control.toggle(), /denied/);
  assert.equal(stage.children, children); control.dispose();
});
