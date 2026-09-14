import assert from "node:assert/strict";
import test from "node:test";
import { LiveRecordingDeadline } from "../custom_components/media_bridge/frontend/live-recording-deadline.js";

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
