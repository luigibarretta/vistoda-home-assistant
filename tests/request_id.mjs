import assert from "node:assert/strict";
import test from "node:test";

import { newRequestId } from "../custom_components/media_bridge/frontend/request-id.js";

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

test("uses randomUUID when the page is a secure context", () => {
  assert.equal(newRequestId({ randomUUID: () => "from-randomUUID" }), "from-randomUUID");
});

test("falls back to getRandomValues on plain http, where randomUUID is undefined", () => {
  const insecure = { getRandomValues: (bytes) => crypto.getRandomValues(bytes) };
  const first = newRequestId(insecure);
  assert.match(first, UUID);
  assert.notEqual(first, newRequestId(insecure));
});

test("the fallback sets the version and variant bits", () => {
  const zeros = { getRandomValues: (bytes) => bytes.fill(0xff) };
  assert.equal(newRequestId(zeros), "ffffffff-ffff-4fff-bfff-ffffffffffff");
});
