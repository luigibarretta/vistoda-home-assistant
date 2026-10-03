import assert from "node:assert/strict";
import test from "node:test";
import { ADVANCED_COPY } from "../custom_components/media_bridge/frontend/panel-copy.js";
import { autoBackupError, autoBackupHint }
  from "../custom_components/media_bridge/frontend/network-archive-auto.js";

test("storage readiness reasons become actionable, translated messages", () => {
  const reasons = ["network_mount_missing", "network_mount_not_writable", "network_mount_low_space",
    "network_mount_unavailable", "invalid_storage_name", "future_reason"];
  const messages = reasons.map((message) => autoBackupError({ code: "storage_unavailable", message }));
  assert.equal(new Set(messages).size, reasons.length);
  assert.match(messages[0], /non montato/);
  assert.equal(autoBackupError({ code: "unauthorized" }), "Serve un account amministratore di Home Assistant.");
  assert.equal(autoBackupError(new Error("offline")), "Impossibile aggiornare il backup automatico.");
  for (const text of [...messages, autoBackupError({ code: "unauthorized" }), autoBackupError(null)]) {
    assert.ok(Object.hasOwn(ADVANCED_COPY, text), text);
  }
});

test("non-administrators get an explanation instead of an editable switch", () => {
  assert.match(autoBackupHint(false, { enabled: true }), /Solo un amministratore/);
  assert.equal(autoBackupHint(true, null), "Stato del backup automatico non disponibile.");
  assert.match(autoBackupHint(true, { enabled: false }), /registrazioni Locale HA/);
  for (const text of [autoBackupHint(false), autoBackupHint(true), autoBackupHint(true, {})]) {
    assert.ok(Object.hasOwn(ADVANCED_COPY, text), text);
  }
});
