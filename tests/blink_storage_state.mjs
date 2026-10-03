import assert from "node:assert/strict";
import test from "node:test";
import { ADVANCED_COPY } from "../custom_components/media_bridge/frontend/panel-copy.js";
import { ACTION_LABELS, backupFailure, nativeUsbState, usbBlocked, usbNotice }
  from "../custom_components/media_bridge/frontend/blink-storage-state.js";
import { commandErrorMessage } from "../custom_components/media_bridge/frontend/blink-storage-refresh.js";

const storage = (usb_state, extra = {}) => ({ status: { usb_state, ...extra } });

test("every official Blink USB screen has an authored, translated notice", () => {
  for (const state of ["format_required", "incompatible", "memory_full", "unavailable", "unmounted"]) {
    const notice = usbNotice(storage(state));
    assert.ok(notice, state);
    for (const key of ["title", "text", "badge", "warning"]) {
      if (notice[key]) assert.ok(ADVANCED_COPY[notice[key]], `${state}.${key}`);
    }
    if (notice.link) assert.ok(ADVANCED_COPY[notice.link[0]] && notice.link[1].startsWith("https://support.blinkforhome.com/"));
  }
  for (const label of Object.values(ACTION_LABELS)) assert.ok(ADVANCED_COPY[label], label);
  assert.equal(usbNotice(storage("active")), null);
  assert.equal(usbNotice(storage("")), null);
  assert.equal(usbNotice({}), null);
});

test("states follow the native screens, actions and fallbacks", () => {
  assert.equal(usbNotice(storage("format_required")).title, "Formatta chiavetta USB");
  assert.equal(usbNotice(storage(" FORMAT_REQUIRED ")).action, "format");
  assert.equal(usbNotice(storage("unmounted")).action, "mount");
  assert.equal(usbNotice(storage("memory_full")).action, "eject");
  assert.equal(usbNotice(storage("unavailable")).action, undefined);
  // LocalStorageState.get: any unknown value is INCOMPATIBLE; the Incompatible
  // screen sends a full drive to MemoryFull first.
  assert.equal(nativeUsbState(storage("brand_new_state")), "incompatible");
  assert.equal(nativeUsbState(storage("incompatible", { usb_storage_full: true })), "memory_full");
  assert.equal(nativeUsbState(storage("")), "");
});

test("only unreadable states hide the usage gauge and empty index", () => {
  for (const state of ["format_required", "unavailable", "unmounted", "incompatible", "unknown"]) {
    assert.equal(usbBlocked(storage(state)), true, state);
  }
  for (const state of ["memory_full", "active", ""]) assert.equal(usbBlocked(storage(state)), false, state);
});

test("active drive shows the native backup and almost-full banners", () => {
  assert.equal(usbNotice(storage("active", { backup_in_progress: true, storage_warning: 3 })).title, "Backup in corso");
  assert.equal(usbNotice(storage("active", { storage_warning: 3 })).title, "L’archiviazione locale è quasi piena");
  assert.equal(usbNotice(storage("active", { storage_warning: 2 })), null);
});

test("backup results map to the native failure reasons", () => {
  const at = "2026-09-23T20:38:19+00:00";
  assert.equal(backupFailure({ last_backup_completed: at, last_backup_result: "success" }), null);
  assert.equal(backupFailure({ last_backup_result: "no_usb" }), null);
  assert.equal(backupFailure({ last_backup_completed: at, last_backup_result: "usb_removed" }), "La chiavetta USB non era presente");
  assert.equal(backupFailure({ last_backup_completed: at, last_backup_result: "sm_offline" }), "Il Sync Module era offline");
  assert.equal(backupFailure({ last_backup_completed: at, last_backup_result: "general" }), "");
});

test("command errors distinguish rejected, pending and unauthorized outcomes", () => {
  assert.match(commandErrorMessage({ code: "rejected" }, "x"), /rifiutato/);
  assert.match(commandErrorMessage({ code: "pending" }, "x"), /aggiornerà/);
  assert.match(commandErrorMessage({ code: "unauthorized" }, "x"), /amministratore/);
  assert.equal(commandErrorMessage({ code: "unavailable" }, "fallback"), "fallback");
  for (const code of ["rejected", "pending", "invalid_state", "unauthorized"]) {
    assert.ok(ADVANCED_COPY[commandErrorMessage({ code }, "")], code);
  }
});
