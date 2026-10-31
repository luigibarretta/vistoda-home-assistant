import assert from "node:assert/strict";
import test from "node:test";
import { deletePlan } from "../custom_components/media_bridge/frontend/archive-delete.js";

test("deleting archived copies names every id and warns about shared clips", () => {
  const copies = [{ id: "ezviz/front-door/a.mpegps" }, { id: "shared/hiv20261028T190000Z-b.mpegps", shared: true }];
  assert.deepEqual(deletePlan(copies), {
    ids: ["ezviz/front-door/a.mpegps", "shared/hiv20261028T190000Z-b.mpegps"],
    prompt: "Eliminare {p0} copie? Quelle condivise spariscono anche da SceneTrove.",
  });
  assert.equal(deletePlan(copies.slice(0, 1)).prompt, "Eliminare {p0} copie archiviate?");
  assert.deepEqual(deletePlan([]).ids, []);
});
