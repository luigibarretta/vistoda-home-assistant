import assert from "node:assert/strict";
import test from "node:test";

import {
  cameraDraft,
  commitDraft,
  reconcileDraft,
  stagedField,
  stageValue,
} from "../custom_components/media_bridge/frontend/blink-setting-draft.js";

const settings = {
  revision: "r1",
  settings: [
    { key: "early_notification", value: true },
    { key: "video_quality", value: "standard" },
  ],
};

test("drafts stay isolated by stable camera alias and reconcile provider values", () => {
  const drafts = new Map();
  const balcony = cameraDraft(drafts, "balcony");
  const kitchen = cameraDraft(drafts, "kitchen");
  stageValue(settings, balcony, "early_notification", false);
  assert.equal(stagedField(settings.settings[0], balcony).value, false);
  assert.equal(kitchen.size, 0);
  reconcileDraft({ ...settings, settings: [{ key: "early_notification", value: false }] }, balcony);
  assert.equal(balcony.size, 0);
});

test("one batch chains revisions and rolls applied fields back in reverse order", async () => {
  const calls = [];
  const hass = { callWS: async (message) => {
    calls.push(message);
    if (message.key === "video_quality" && message.value === "best") throw new Error("rejected");
    return { ...settings, revision: `r${calls.length + 1}` };
  } };
  const draft = new Map([
    ["early_notification", false],
    ["video_quality", "best"],
  ]);
  await assert.rejects(commitDraft(hass, "balcony", settings, draft), (error) => {
    assert.equal(error.rollbackFailed, false);
    return true;
  });
  assert.deepEqual(calls.map(({ key, value }) => [key, value]), [
    ["early_notification", false],
    ["video_quality", "best"],
    ["early_notification", true],
  ]);
  assert.deepEqual(calls.map(({ revision }) => revision), ["r1", "r2", "r2"]);
});

test("a successful batch returns the final verified provider state", async () => {
  const hass = { callWS: async (message) => ({ ...settings, revision: `${message.key}-done` }) };
  const result = await commitDraft(
    hass, "balcony", settings, new Map([["early_notification", false]]),
  );
  assert.equal(result.revision, "early_notification-done");
});
