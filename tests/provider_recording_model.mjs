import assert from "node:assert/strict";
import test from "node:test";

const model = await import(new URL(
  "../custom_components/media_bridge/frontend/provider-recording-model.js",
  import.meta.url,
));

test("Blink and EZVIZ recording commands expose no provider credentials", () => {
  const blink = { provider: "blink", alias: "balcone" };
  const ezviz = { provider: "ezviz", alias: "front-door", entryId: "entry-1" };
  assert.deepEqual(model.recordingCommand(blink, "list"), {
    type: "blink_live_bridge/recordings/list",
  });
  assert.deepEqual(model.recordingCommand(blink, "create"), {
    type: "blink_live_bridge/recordings/create", alias: "balcone",
  });
  assert.deepEqual(model.recordingCommand(ezviz, "delete"), {
    type: "media_bridge/ezviz/recordings/delete", entry_id: "entry-1",
  });
});

test("recording inventories stay camera-scoped and newest first", () => {
  const items = [
    { camera: "balcone", requested_at: "2026-01-01T10:00:00Z" },
    { camera: "cucina", requested_at: "2026-01-03T10:00:00Z" },
    { camera: "balcone", requested_at: "2026-01-02T10:00:00Z" },
  ];
  assert.deepEqual(
    model.cameraRecordings(items, "balcone").map((item) => item.requested_at),
    ["2026-01-02T10:00:00Z", "2026-01-01T10:00:00Z"],
  );
});

test("signed media paths stay on Home Assistant", () => {
  assert.equal(
    model.recordingMediaPath({ provider: "blink" }, "id"),
    "/api/blink_live_bridge/v1/recordings/id/media",
  );
  assert.equal(
    model.recordingMediaPath({ provider: "ezviz", entryId: "entry" }, "id"),
    "/api/media_bridge/ezviz/recordings/entry/id",
  );
});
