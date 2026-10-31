# Phase 4: shared archive, SceneTrove event markers, deletion — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One copy of an EZVIZ camera's clips and events, visible in Vistoda and
SceneTrove; SceneTrove shows event markers; Vistoda can delete archived events
and clips, warning when the file is shared.

**Architecture:** In `shared` mode the integration writes into SceneTrove's own
device folder, reached through a second Home Assistant network storage: events
under `_events/`, microSD clips as `hiv<stamp>Z-<uuid>.mpegps` moved from the
bridge after a SHA-256 check. SceneTrove serves `_events/` through its own
endpoint (outside the clip scan and the timeline fingerprint) and draws markers
on the day track.

**Tech Stack:** HA integration (Python, vanilla JS), SceneTrove (Rust + Svelte 5),
homelab-ansible (NFS export, HA network storage).

**Spec:** `docs/superpowers/specs/2026-10-29-event-archive-and-scenetrove-link-design-part2.md` sections 5–8.

## Rulings taken while planning (spec deviations)

- **Shared folder = SceneTrove's device folder, not `<root>/shared/<device>/`.**
  SceneTrove already keeps devices at `/pool1/security/scenetrove-devices/<device>`
  on nas-01. A second HA network storage (option `shared_storage`, e.g.
  `scenetrove_devices`) exports that root; the shared folder is
  `<shared mount>/<scenetrove_device>/`. Nothing moves, SceneTrove needs no new
  mount, and existing SceneTrove clips stay visible. Cost if wrong: one more option.
- **Only microSD clips (MPEG-PS) move in this phase.** SceneTrove plays only
  MPEG-PS/MP4 named `hiv…Z-<lowercase uuid>`; live TS recordings have no
  SHA-256-verifiable MP4 form. TS recordings keep today's behaviour (bridge +
  manual network copy). Cost if wrong: live captures are not shared yet.
- **SceneTrove events endpoint is `/api/device-events`** (`/api/events` is the SSE stream).

## Global Constraints

- 250 lines per maintained Vistoda file (strings/translations are at the limit:
  compact or split before adding keys); SceneTrove LOC baseline (400 + ratchet).
- SceneTrove brand gate: no vendor names in that repo (events are "camera events").
- Older bridges/SceneTrove keep working: `shared` mode needs `shared_storage`
  ready and `scenetrove_url` set, otherwise the option is refused.
- Heavy builds one at a time through the build lock.
- `_events/` is read-only for SceneTrove; Vistoda never deletes files outside the
  entry's camera folder (`events/ezviz/<alias>/`) or its shared device folder.

## Review Focus

1. **Bridge copy deleted before the shared copy is durable** → never: delete only after fsync + rename + SHA-256 match (`test_bridge_copy_is_kept_when_the_digest_differs`).
2. **Event listed twice** (old `events/` and `_events/`) → de-duplicated by `alarm_id` (`test_events_from_both_locations_are_listed_once`).
3. **Path traversal** in delete ids or SceneTrove picture paths → refused (`test_delete_refuses_paths_outside_the_camera`, Rust `event_picture_rejects_traversal`).
4. **SceneTrove rebuilding the timeline for every new event** → `_events/` excluded from media walk and fingerprint (Rust `events_do_not_change_the_fingerprint`).
5. **Non-admin deleting** → refused before any filesystem access (`test_delete_requires_admin`).

---

### Task 1: Shared location and options (integration)

**Files:** Create `shared_archive.py` (paths: `shared_device_dir(mount, device)`,
`shared_clip_name(recording) -> str` = `hiv<%Y%m%dT%H%M%SZ of sd_start>-<id>.mpegps`,
`shared_events_root`); modify `options_flow.py` (`clip_destination` select
`vistoda|shared`, `shared_storage` name; `shared` requires `scenetrove_url` and a
ready `shared_storage`), `const.py`, strings/translations (compact first).
Tests: `tests/test_shared_archive.py`.

- [ ] Tests `shared_clip_names_follow_scenetrove`, `shared_mode_needs_a_link_and_ready_storage` → RED → implement → GREEN → commit.

### Task 2: Events in shared mode, read from both locations

**Files:** `event_archive.py` (layout parts become a parameter; `_events` layout
`<device>/_events/YYYY/MM`), `ezviz_event_archiver.py` (write to the current
mode's location), `event_archive_api.py` (list and picture merge both locations,
de-duplicate by `alarm_id`, newest first, then paginate).

- [ ] Tests `test_shared_mode_writes_events_under_events_folder`, `test_events_from_both_locations_are_listed_once` → RED → implement → GREEN → commit.

### Task 3: Clip mover (integration)

**Files:** Create `shared_clip_mover.py` (async poller per shared-mode EZVIZ entry,
every 60 s: bridge recordings `ready` + MPEG-PS + not yet moved → stream with the
`recording_backup` helpers to `.partial`, verify bytes + SHA-256 against the
manifest, fsync, rename to `shared_clip_name`, write the sidecar, then
`delete_provider_recording`); wire in `__init__.py` setup/unload.

- [ ] Tests `test_ready_microsd_clip_is_moved_then_deleted_on_the_bridge`, `test_bridge_copy_is_kept_when_the_digest_differs`, `test_live_ts_recordings_are_left_alone` → RED → implement → GREEN → commit.

### Task 4: Deletion (integration + panel)

**Files:** Create `archive_delete_websocket.py`: `media_bridge/events/delete`
(ids of the entry's camera, both locations) and
`media_bridge/network_archive/delete` (EZVIZ copies and shared `hiv…` clips of
the entry's device); admin only; returns `{deleted, failed}`. Inventory lists
shared clips. Panel: delete per item and bulk in the events card and the archive
list, with `confirm` text "La clip verrà eliminata anche da SceneTrove." in
shared mode (IT/EN copy).

- [ ] Tests `test_delete_requires_admin`, `test_delete_refuses_paths_outside_the_camera`, `test_shared_delete_reports_partial_failures`; node test for the confirm text choice → RED → implement → GREEN → browser check → commit.

### Task 5: SceneTrove reads camera events (backend)

**Files:** `src/media.rs` / `src/server_timeline_freshness.rs` (skip `_events`),
new `src/device_events.rs` (read `<device>/_events/YYYY/MM/*.json`, validated
names, generic `{id, at, category, title, picture}`), routes
`GET /api/device-events?device=&from=&to=` and
`GET /api/device-events/picture?device=&id=` (MediaRead scope, path confined to
`_events/`).

- [ ] Rust tests `events_are_read_from_the_events_folder`, `events_do_not_change_the_fingerprint`, `event_picture_rejects_traversal` → RED → implement → GREEN → `ci-local` → commit.

### Task 6: SceneTrove markers (UI)

**Files:** `ui/src/lib/device-events.js` (fetch + group by `localDay`),
`TimelineTrack.svelte` (marker per event; tap → picture popover + select the
covering clip via `resolveInstant`), IT/EN copy; unit test for grouping,
Playwright case on the mock (`dev/mock.js` serves two events).

- [ ] Tests → RED → implement → GREEN → `ci-local --quick` + e2e → commit, push, CI.

### Task 7: Release and Luigi's install

- [ ] Integration 0.50.0 (all CI steps, tag, CI); SceneTrove release through its pipeline.
- [ ] homelab-ansible: NFS export of `/pool1/security/scenetrove-devices` to iot-01
  (squashed to 1000:1000, read-write) and an HA network storage
  `scenetrove_devices` following `configure-ha-vistoda-archive-nfs.yml`.
  **Confirm with Luigi before applying** (it opens SceneTrove's archive to HA).
- [ ] Options on the front-door entry: `shared_storage=scenetrove_devices`,
  `clip_destination=shared`; verify a microSD save lands in
  `spioncino/hiv…mpegps`, the bridge copy is gone, the event appears in
  `_events/`, SceneTrove shows the marker and the clip, and deleting from
  Vistoda warns and removes it for both.
