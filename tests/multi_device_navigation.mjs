import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";

const frontend = new URL("../custom_components/media_bridge/frontend/", import.meta.url);
const source = async (...names) => (await Promise.all(names.map((name) =>
  readFile(new URL(name, frontend), "utf8")))).join("\n");

test("Blink preserves the selected camera and scopes its Sync Module alarm", async () => {
  const blink = await source("blink-view.js", "blink-view-navigation.js");
  assert.match(blink, /firstEntity\(device, "camera"\)\?\.entity_id === this\._selectedCameraId/);
  assert.match(blink, /this\._stopLiveForCameraChange\(\)/);
  assert.match(blink, /state\?\.attributes\?\.network_id/);
  assert.match(blink, /String\(networkId\)/);
  assert.match(blink, /networkId == null && alarms\.length === 1 \? alarms\[0\] : null/);
});

test("EZVIZ pages by stable entity and binds actions to exact entries", async () => {
  const ezviz = await source("ezviz-view.js", "ezviz-view-navigation.js");
  assert.match(ezviz, /entry\.entry_id === entryId/);
  assert.match(ezviz, /matching\.length === 1/);
  assert.match(ezviz, /firstEntity\(device, "camera"\)\?\.entity_id === this\._selectedCameraId/);
  assert.match(ezviz, /generation !== this\._cameraGeneration/);
  assert.match(ezviz, /this\._snapshotTimes\.set\(cameraId/);
  assert.doesNotMatch(ezviz, /connectedCallback\(\).*_refresh/s);
});

test("shared archives invalidate in-flight device requests", async () => {
  const archive = await source(
    "provider-recordings.js",
    "provider-recordings-actions.js",
    "provider-recording-list-manager.js",
    "provider-recording-bulk-lists.js",
    "provider-recording-player.js",
  );
  assert.match(archive, /this\._generation \+= 1/);
  assert.match(archive, /this\._isCurrent\(context\)/);
  assert.match(archive, /generation !== this\.generation/);
  assert.match(archive, /this\._bulkListManager\.reset\(\)/);
  assert.match(archive, /generation !== this\._generation\) return false/);
  assert.doesNotMatch(archive, /!this\._isCurrent\(context\)\) this\.\$\("player"\)\.close/);
});
