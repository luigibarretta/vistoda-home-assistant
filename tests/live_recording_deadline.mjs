import assert from "node:assert/strict";
import test from "node:test";
import { LiveRecordingDeadline } from "../custom_components/media_bridge/frontend/live-recording-deadline.js";
import { LiveRecordingMenu } from "../custom_components/media_bridge/frontend/live-recording-menu.js";

test("late provider recording acknowledgement cannot affect a new live", async () => {
  let resolve;
  const nodes = { start: { disabled: false }, status: { textContent: "" },
    destination: { value: "provider" }, duration: { value: "15" } };
  const menu = Object.create(LiveRecordingMenu.prototype);
  Object.assign(menu, { generation: 0, root: { getElementById: id => nodes[id] },
    deadline: new LiveRecordingDeadline(() => assert.fail("stale deadline")),
    _destination() { nodes.start.disabled = false; },
    view: { _current: () => ({ entity_id: "camera.test" }), _hass: {
      states: { "camera.test": { attributes: { alias: "test" } } },
      callWS: () => new Promise(done => { resolve = done; }),
    } } });
  const pending = menu.start();
  menu.resetProvider();
  nodes.status.textContent = "new live";
  resolve({ status: 1 });
  await pending;
  assert.equal(menu.providerSaving, false);
  assert.equal(menu.deadline.remaining, null);
  assert.equal(nodes.status.textContent, "new live");
});

test("provider deadline counts media only and finishes once", () => {
  let finished = 0;
  const timer = new LiveRecordingDeadline(() => finished++);
  const video = { paused: false, readyState: 0, currentTime: 0 };
  timer.start(15);
  for (let i = 0; i < 100; i++) timer.update(video, true);
  assert.equal(timer.remaining, 15);
  video.readyState = 4;
  for (let i = 0; i <= 60; i++) { video.currentTime = i / 4; timer.update(video, true); }
  assert.equal(finished, 1);
  timer.update(video, true); assert.equal(finished, 1);
});
test("reset and reconnect never close a different or stalled live", () => {
  let finished = 0;
  const timer = new LiveRecordingDeadline(() => finished++);
  const video = { paused: false, readyState: 4, currentTime: 0 };
  timer.start(15); timer.update(video, true);
  video.currentTime = 100; timer.update(video, true);
  assert.equal(timer.remaining, 15);
  timer.reset(); video.currentTime += .25; timer.update(video, true);
  assert.equal(finished, 0);
});
