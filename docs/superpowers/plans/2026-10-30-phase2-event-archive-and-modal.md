# Phase 2: Vistoda event archive and event modal — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Archive EZVIZ alarms (metadata and picture) on the Vistoda network
archive with no count limit, browse that archive from the panel, list EZVIZ
clip copies in the network archive, and open any event in a modal with its
video when one exists.

**Architecture:** A pure filesystem module (`event_archive.py`) owns layout,
atomic writes, listing, pictures and retention. An archiver
(`ezviz_event_archiver.py`) follows the alarms the listener already publishes,
backfills with the bridge's `before` pages, and prunes daily. A websocket and
a picture view expose the archive; the panel card pages it server-side and
opens a native `<dialog>` per event.

**Tech Stack:** Home Assistant custom integration (Python 3.13, aiohttp),
vanilla JS web components, node:test, pytest.

**Spec:** `docs/superpowers/specs/2026-10-29-event-archive-and-scenetrove-link-design.md`
sections 2–3 (part 2 holds sections 4–8, not in this phase).

## Global Constraints

- All code in `vistoda-home-assistant` (`custom_components/media_bridge`). Every maintained file ≤ 250 lines, Markdown included (`scripts/check_loc.py`).
- CI steps to pass before each push: `ruff format --check .`, `ruff check .`, `compileall`, `scripts/check_loc.py`, `pytest`, `node --test tests/*.mjs` (all with `.venv/bin/python`).
- Layout, exact: `<mount>/events/<provider>/<camera>/<YYYY>/<MM>/<YYYYmmddTHHMMSSZ>-<alarm_id>.json` (+ `.jpg`). JSON `schema_version: 1`, keys `provider, camera, alarm_id, occurred_at, category, alarm_type, title, picture, archived_at`. No serials, tokens or vendor URLs.
- Writes: `.partial` → fsync → atomic rename; mount checks of `backup_storage.py` (`network_filesystem`, `safe_directory`, `storage_readiness`); never follow symlinks.
- Options (EZVIZ entries only): `event_archive` bool default `False`; `event_retention_days` int, `0` (forever, default) or 7–3650. Retention deletes event JSON/JPEG only, never clips.
- Access: list and pictures follow `can_access_ezviz_entry`; nothing in this phase deletes clips.
- Modal video rules for this phase: (2) a bridge recording covering the instant → play with the existing `vistoda-provider-recording-player`; (3) else "Salva dalla microSD" via existing `create_sd`, window event − 10 s to event + 50 s, label says it wakes the camera. Rule 1 (SceneTrove) is phase 3.
- Copy: every new UI string in IT (source) and EN (`panel-copy-*.js`), options in `strings.json` and `translations/{en,it}.json`.
- Release: version 0.48.0 (`manifest.json`, `const.py`, `pyproject.toml`), tag `v0.48.0`, CI watched, homelab pin `ha_media_bridge_version`/`ha_media_bridge_release_sha` (= checkout HEAD), `deploy-ha-media-bridge`.

## Review Focus

1. **Network mount missing or read-only while alarms arrive** → no crash, alarms still reach HA, one warning, archiving resumes when the mount returns. Test in Task 3 (`archiver_survives_a_missing_mount`).
2. **Same alarm seen twice** (live + backfill, or restart) → exactly one JSON. Test in Task 1 (`write_event_is_idempotent`).
3. **Hostile names on disk** (symlinked camera dir, `../` alarm id, foreign JSON, 1 MB JSON) → skipped, never read outside the mount. Test in Task 1 (`listing_skips_unsafe_and_foreign_files`).
4. **App restart mid-backfill / bridge without `before`** (older than 0.16) → backfill stops after the first page, no loop. Test in Task 3 (`backfill_stops_without_older`).
5. **Event at the edge of a recording** (exactly at start or end) → counts as covered. Test in Task 6 (`edges_of_a_recording_cover_the_event`).

---

### Task 1: Event archive storage (`event_archive.py`)

**Files:** Create `custom_components/media_bridge/event_archive.py`; Test `tests/test_event_archive.py` (fixture like `tests/test_network_archive.py:13`, patching `network_filesystem` to `"nfs"`).

**Interfaces — Produces:**
- `event_id(occurred_at: int, alarm_id: str) -> str` → `"20261029T082621Z-<alarm_id>"`; raises `ValueError` for ids outside `^[A-Za-z0-9_-]{1,96}$`.
- `write_event(mount: Path, provider: str, camera: str, alarm: dict, jpeg: bytes | None) -> bool` (False when it already exists).
- `list_events(mount: Path, provider: str, camera: str, page: int, page_size: int, day: str = "") -> dict` → `{"items": [...], "pagination": {...}}` with the same pagination keys as `network_archive.inventory`; items `{id, alarm_id, occurred_at, category, alarm_type, title, picture: bool}`, newest first.
- `event_picture(mount: Path, provider: str, camera: str, event: str) -> Path` (checked, `ValueError` otherwise).
- `prune_events(mount: Path, provider: str, camera: str, older_than: int) -> int` (removed count).

- [ ] **Step 1:** Tests `write_event_is_idempotent`, `listing_pages_newest_first_and_filters_by_day`, `listing_skips_unsafe_and_foreign_files` (symlinked dir, bad id, `schema_version` 2, JSON > 16 KiB, provider mismatch), `pictures_are_checked_paths`, `prune_removes_only_old_events`.
- [ ] **Step 2:** `.venv/bin/python -m pytest tests/test_event_archive.py -q` → FAIL (module missing).
- [ ] **Step 3:** Implement (reuse `safe_directory`; the year/month directories are two more `safe_directory` parts).
- [ ] **Step 4:** Same command → PASS. **Step 5:** Commit `feat(events): network event archive storage`.

### Task 2: List EZVIZ copies in the network archive

**Files:** Modify `network_archive.py:12` (`SAFE_PATH`), `checked_file` (provider by top directory, `<recording_id>.<ext>` name, media type), `inventory` provider loop; `frontend/network-archive.js` (download only for `video/mpeg`); Test `tests/test_network_archive.py`, `tests/network_archive_*.mjs` if a model exists.

- [ ] **Step 1:** Test `ezviz_copies_are_listed_with_their_media_type`: an `ezviz/front-door/<uuid>.mpegps` + sidecar (`provider: "ezviz"`, `recording: {recording_id, camera, requested_at, bytes, sha256}`) is listed with `media_type: "video/mpeg"`; a `.ts` one with `video/mp2t`.
- [ ] **Step 2:** RED. **Step 3:** Implement. **Step 4:** GREEN. **Step 5:** Commit `fix(archive): list EZVIZ network copies`.

### Task 3: Options and archiver (`ezviz_event_archiver.py`)

**Files:** Modify `options_flow.py`, `const.py` (`CONF_EVENT_ARCHIVE`, `CONF_EVENT_RETENTION_DAYS`), `strings.json`, `translations/en.json`, `translations/it.json`, `__init__.py`/runtime wiring next to `EzvizAlarmListener`; Create `ezviz_event_archiver.py`; Test `tests/test_ezviz_event_archiver.py`, `tests/test_options_flow*.py`.

**Interfaces — Consumes:** Task 1 functions; `client.ezviz_alarms(alias)` / `(alias, before=n)` (`older`); `client.ezviz_alarm_picture(alias, alarm_id) -> bytes | None`; dispatcher `ezviz_alarm_signal(entry_id)` data from `EzvizAlarmListener._publish`.
**Produces:** `class EzvizEventArchiver(hass, entry, client, alias)` with `async start()`, `async stop()`, `async archive(data: dict)`, `async backfill()`, `async prune()`.

- [ ] **Step 1:** Tests: `options_reject_retention_between_one_and_six`, `enabling_needs_a_ready_mount`, `live_alarm_is_archived_with_its_picture`, `backfill_walks_older_pages_until_known`, `backfill_stops_without_older`, `archiver_survives_a_missing_mount`, `prune_runs_with_retention_only`.
- [ ] **Step 2:** RED. **Step 3:** Implement; filesystem work in `hass.async_add_executor_job`; daily prune via `async_track_time_interval`; one warning per outage. Option labels (IT): "Archivia gli eventi nell'archivio di rete" / "Conserva gli eventi archiviati (giorni, 0 = per sempre)"; EN: "Archive events on network storage" / "Keep archived events (days, 0 = forever)".
- [ ] **Step 4:** GREEN. **Step 5:** Commit `feat(events): archive EZVIZ alarms on network storage`.

### Task 4: Websocket and picture view

**Files:** Create `event_archive_api.py` (websocket `media_bridge/events/list` {`entry_id`, `page`=1, `page_size`=10 (1–100), optional `day` `YYYY-MM-DD`} → `{"enabled": bool, "items", "pagination"}`; view `/api/media_bridge/events/{entry_id}/{event}.jpg`); register in the integration setup; Test `tests/test_event_archive_api.py`.

- [ ] **Step 1:** Tests `list_requires_camera_access`, `disabled_archive_answers_enabled_false`, `items_carry_signed_picture_paths`, `picture_view_rejects_unsafe_names`.
- [ ] **Step 2:** RED. **Step 3:** Implement (`can_access_ezviz_entry`; `Cache-Control: private`; picture path `/api/media_bridge/events/<entry_id>/<id>.jpg` in items when `picture` is true). **Step 4:** GREEN. **Step 5:** Commit `feat(events): archived event list and pictures`.

### Task 5: Events card reads the archive

**Files:** Modify `frontend/ezviz-alarms.js`, `frontend/ezviz-alarm-model.js` (`archiveRows(items)` mapping archive items to the card row shape); Test `tests/ezviz_alarm_model.mjs`.

- [ ] **Step 1:** Test `archive_items_become_card_rows` (picture path kept only when it matches the integration's own route).
- [ ] **Step 2:** RED. **Step 3:** The card first calls `media_bridge/events/list`; `enabled: true` → server pages (page, page_size, total from `pagination`); otherwise the 0.47.0 bridge path. Row click dispatches `alarm-open` with `{ index }`. **Step 4:** GREEN. **Step 5:** Commit `feat(panel): events card pages the event archive`.

### Task 6: Event modal

**Files:** Create `frontend/ezviz-alarm-dialog.js` (`<vistoda-ezviz-alarm-dialog>`, native `<dialog>` like `camera-live-dialog.js`: focus trap via `showModal`, Esc, labelled close, full screen under 600 px, ←/→ keys); Modify `frontend/ezviz-alarm-model.js` (`alarmVideo(recordings, occurredAt) -> {kind: "play", recording} | {kind: "save", start, end}`), `frontend/ezviz-alarms.js` (open on `alarm-open`), `panel-copy-*.js`; Test `tests/ezviz_alarm_model.mjs`.

- [ ] **Step 1:** Tests `a_covering_recording_is_played` (sd: `sd_start..sd_end`; live: `started_at..started_at+actual_duration_seconds`), `edges_of_a_recording_cover_the_event`, `otherwise_the_microsd_window_is_offered` (`start = t-10`, `end = t+50`), `failed_or_pending_recordings_are_ignored`.
- [ ] **Step 2:** RED. **Step 3:** Implement; recordings from `media_bridge/ezviz/recordings/list`; play with `vistoda-provider-recording-player.open(hass, config, item)`; save with the existing `ezviz-sd-save.js` call. Copy: "Video", "Riproduci la registrazione", "Salva dalla microSD", "Sveglia la telecamera e consuma batteria.", "Evento precedente", "Evento successivo", "Chiudi" (+ EN). **Step 4:** GREEN. **Step 5:** Commit `feat(panel): event modal with picture and video`.

### Task 7: Docs, release and deploy

**Files:** `docs/adr/0028-event-archive.md`, `docs/reconnect-and-network-backup.md` + `.it.md` (event archive section), version files (0.48.0).

- [ ] **Step 1:** All CI steps above → pass. Commit `feat(events): network event archive and event modal (0.48.0)`, tag `v0.48.0`, push; watch Gitea CI green.
- [ ] **Step 2:** homelab: pin `ha_media_bridge_version: 0.48.0` and the HEAD SHA, `tests/test_vistoda_deploy.py`, commit, push, `deploy-ha-media-bridge` → `failed=0`.
- [ ] **Step 3:** Enable `event_archive` on the front-door entry (options flow; if the API token cannot, ask Luigi to tick it), then verify JSON/JPEG under `events/ezviz/front-door/` on the NAS share and the card listing them with a page count.
