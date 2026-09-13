import test from "node:test";
import assert from "node:assert/strict";
import { stopLiveMedia } from "../custom_components/media_bridge/frontend/stop-live-media.js";

test("teardown silences and releases only this viewer through shadow boundaries", () => {
  const calls = [];
  const video = { localName: "video", muted: false,
    srcObject: { getTracks: () => [{ stop: () => calls.push("track") }] },
    pause: () => calls.push("pause"), load: () => calls.push("load"),
    removeAttribute: name => calls.push(name) };
  const otherViewer = { muted: false };
  stopLiveMedia({ children: [{ shadowRoot: { children: [video] } }] });
  assert.equal(video.muted, true);
  assert.equal(video.srcObject, null);
  assert.deepEqual(calls, ["pause", "track", "src", "load"]);
  assert.equal(otherViewer.muted, false);
  stopLiveMedia(null);
});
