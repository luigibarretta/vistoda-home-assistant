import assert from "node:assert/strict";
import test from "node:test";

import {
  RECORDINGS_PER_PAGE,
  recordingDate,
  recordingDuration,
  recordingPage,
  recordingSize,
} from "../custom_components/media_bridge/frontend/recording-table.js";

const recordings = Array.from({ length: 19 }, (_, index) => ({
  recording_id: String(index),
  started_at: 1_786_800_000 + index,
  ended_at: 1_786_800_065 + index,
  bytes: 2048,
}));

test("archive pagination is bounded and clamps invalid pages", () => {
  assert.equal(RECORDINGS_PER_PAGE, 8);
  assert.deepEqual(recordingPage(recordings, 2).items.map((item) => item.recording_id),
    ["8", "9", "10", "11", "12", "13", "14", "15"]);
  assert.equal(recordingPage(recordings, 99).page, 3);
  assert.equal(recordingPage([], -5).page, 1);
});

test("archive metadata receives readable duration, date and size labels", () => {
  assert.equal(recordingDuration(recordings[0]), "1 min 05 s");
  assert.equal(recordingDuration({ started_at: 10, ended_at: 3 }), "0 s");
  assert.equal(recordingSize(2048), "2 KiB");
  assert.equal(recordingSize(1_572_864), "1.5 MiB");
  assert.match(recordingDate(recordings[0], "it-IT", "Europe/Rome"), /2026/);
});
