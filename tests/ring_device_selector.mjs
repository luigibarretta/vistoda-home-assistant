import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";

const source = await Promise.all(["ring-view.js", "ring-device-selector.js"].map((name) =>
  readFile(new URL(`../custom_components/media_bridge/frontend/${name}`, import.meta.url), "utf8")))
  .then((parts) => parts.join("\n"));

test("Ring multi-entry selector is an explicit accessible card list", () => {
  assert.match(source, /id="device-options" role="listbox"/);
  assert.match(source, /className = "device-card"/);
  assert.match(source, /item\.setAttribute\("aria-selected", String\(selected\)\)/);
  assert.match(source, /item\.setAttribute\("aria-label", `\$\{name\}, \$\{location\}, \$\{available\}`\)/);
  assert.match(source, /ArrowRight.*ArrowDown.*ArrowLeft.*ArrowUp.*Home.*End/);
  assert.match(source, /\.device-options\{display:flex; overflow-x:auto/);
});

test("Ring selector keeps exact entry IDs and single-entry hidden behavior", () => {
  assert.match(source, /item\.dataset\.entryId = entry\.entry_id/);
  assert.match(source, /host\._selectEntry\(card\.dataset\.entryId\)/);
  assert.match(source, /host\.\$\("device-picker"\)\.hidden = host\._entries\.length < 2/);
  assert.match(source, /await this\._audio\?\.destroy\(\)/);
  assert.match(source, /saveRingEntry\(host\._storage, host\._entry\.entry_id\)/);
});

test("Ring switching cannot acknowledge a stale incoming call", () => {
  assert.match(source, /this\._entryGeneration \+= 1/);
  assert.match(source, /entry\.entry_id !== this\._requestedEntryId/);
  assert.match(source, /this\._answerMode = false;\s*this\._callId = ""/);
  assert.match(source, /const entry = this\._entry;\s*const callId = this\._callId;\s*const generation = this\._entryGeneration/);
  assert.match(source, /entry_id: entry\.entry_id,\s*call_id: callId/);
  assert.match(source, /generation === this\._entryGeneration && entry === this\._entry && callId === this\._callId/);
});
