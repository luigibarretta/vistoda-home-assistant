# Event archive, event modal and the SceneTrove link

Date: 2026-10-29. Owner: Luigi Barretta. Status: approved 2026-10-29.

Repositories: `vistoda-ezviz` (bridge app), `vistoda-addons` (app catalog),
`vistoda-home-assistant` (integration and panel, this repo), `scenetrove`.

## Intent

The question a user asks is "who came to the door while I was out?". Today the
EZVIZ events card in the Vistoda panel lists recent alarms with a small picture,
while the video of that moment lives elsewhere (a saved microSD recording, a
network-archive copy, or SceneTrove). Answering the question means hopping
between places and timestamps.

Vistoda must answer it on its own. SceneTrove is a specialised, optional
companion for clear timelines and browsing clips over time: Vistoda presents
it, and when a user has an instance, the two work together without duplicate
copies.

## Goals

1. **User-set alarm retention in the bridge.** The app keeps the newest N
   alarms per camera; N becomes an app option with clear disclaimers.
2. **Event archive in Vistoda, without SceneTrove.** Alarms (metadata and
   picture) are archived on the existing Vistoda network archive with no count
   limit, and the panel browses that archive.
3. **Event modal.** Tapping an event opens a modal: large picture, time,
   category, title, previous/next event, and the video of that moment when
   one is available (see "Video in the modal").
4. **SceneTrove link.** Vistoda presents SceneTrove and lets the user set the
   URL of their instance. With it set, "open the video" jumps to SceneTrove at
   that instant.
5. **Clip destination and shared archive.** With SceneTrove linked, the user
   chooses where clips are saved: Vistoda, or a shared archive that both apps
   use with a single copy of each file (SceneTrove sees every clip there).
6. **Events in SceneTrove.** With the shared archive, SceneTrove shows the
   archived events as markers on its timeline.

## Non-goals (this design)

- Automatically saving a clip for every event. Each microSD playback wakes a
  battery camera; on 2026-10-26/27 a bulk microSD sync drained the front-door
  viewer from 77 % to 1 % in 14 hours. Clips stay user-initiated (the existing
  "Salva" from microSD) or come from SceneTrove's own sync.
- Deleting files from disk inside SceneTrove (it has no such endpoint today).
- Fetching older EZVIZ cloud history by date (beyond what the bridge retains).
- Other providers (Blink, Ring) in the event archive; the format must not
  prevent adding them later.

## Anti-goals (failure even if it technically works)

- Two copies of the same clip when the user chose the shared archive.
- A delete that silently removes a file the other app still shows, or that
  removes it without saying so (see "Deletion").
- Camera vendor names in the `scenetrove` repository: its brand gate
  (`scripts/check-brand-identity.mjs`) rejects them in code, docs, i18n and
  plans. SceneTrove code and docs speak of "camera events" generically.
- Tokens, bridge secrets or pre-signed vendor URLs in links, files or logs.
- Growing Home Assistant backups or `/data` without the user having been told.

## Current state (facts, 2026-10-29)

- Bridge: `MAX_EVENTS = 200` per camera (`vistoda-ezviz/src/alarms/store.rs`),
  pictures share `TOTAL_PICTURE_BYTES = 256 MiB` split per camera
  (`src/alarms/mod.rs`), state in `/data/alarms/<alias>/history.json` and
  `pictures/<id>.jpg`. Since 0.16.0, `GET /v1/cameras/{c}/alarms?before=<seq>`
  pages back through every retained alarm (`older` cursor); `after`/`wait` is
  the live cursor. App options live in `vistoda-addons/vistoda_ezviz/config.yaml`
  and reach the bridge as `EZVIZ_BRIDGE_*` env through
  `packaging/home-assistant/run.sh`; `src/config.rs` reads them with bounds.
- Integration 0.47.0: the events card pages through bridge history (shared
  page-size selector and archive pager); `EzvizAlarmListener` tails the live
  cursor. Options are per config entry (`options_flow.py`: `backup_storage`,
  `reconnect_account`, `blink_usb_auto_backup`).
- Network archive: root `/media/<backup_storage>` (default `vistoda_archives`,
  an NFS/CIFS Supervisor mount, read-write, 512 MiB free required; checks in
  `backup_storage.py`). Layout `<root>/<provider>/<camera>/<id>.<ext>` plus
  `<file>.json` sidecar, written `.partial` → fsync → atomic rename
  (`recording_backup.py`). EZVIZ copies land in `ezviz/` but the inventory
  regex lists only `blink` and `blink-usb` (`network_archive.py:12, :79`).
  Nothing deletes from the archive (ADR 0024).
- EZVIZ recordings ("Salva" from microSD, live recordings) are created inside
  the bridge (`/data/recordings`) and copied to the network archive by HA.
- SceneTrove: a device is a folder under `/data/sd/<device>`; it indexes
  folders it did not write (read-only works for browsing). File times come
  from names such as `hiv<YYYYmmddTHHMMSS>Z-<id>.mpegps` (the bridge already
  writes that form for SceneTrove). No timestamp deep link, no event model,
  no delete-from-disk. API auth: `scenetrove_pat_` Bearer tokens with scopes.

## Design

### 1. User-set alarm retention (bridge + catalog)

- New app options in `vistoda-addons/vistoda_ezviz/config.yaml`:
  - `alarm_history_limit`: integer 50–2000, default 200 (alarms per camera).
  - `alarm_picture_budget_mib`: integer 64–2048, default 256 (all cameras).
- Mapped to `EZVIZ_BRIDGE_ALARM_HISTORY_LIMIT` / `EZVIZ_BRIDGE_ALARM_PICTURE_BUDGET_MIB`
  in `run.sh`, read in `src/config.rs` with the same bounds (out of range →
  clamp and log once, never fail startup). `MAX_EVENTS` and
  `TOTAL_PICTURE_BYTES` become runtime values passed to `CameraHistory`.
- Lowering the limit trims the oldest alarms (and their pictures) at the next
  start; this is stated in the disclaimer.
- `CameraHistory::knows()` scans every alarm; with up to 2000 per camera it
  gets an id index (`HashSet`) kept in step with push/evict.
- Disclaimer (option description in the app translations, IT and EN), in
  substance: "Alarms and their pictures are kept on Home Assistant's own disk
  and are included in Home Assistant backups. 2000 alarms with pictures can
  take up to the picture budget you set. For a long history use the Vistoda
  event archive on network storage, or SceneTrove. Lowering the value deletes
  the oldest alarms at the next start."
- Upper bound 2000 is my call: `history.json` is rewritten atomically on every
  insert and the store is scanned linearly; 2000 keeps both cheap. Long
  history belongs to the archive (section 2).

### 2. Vistoda event archive (integration)

- New per-entry option `event_archive` (bool, default off) in the options
  flow, available when `backup_storage` is a valid mount. Description says
  where events go and that the archive has no automatic deletion unless
  `event_retention_days` is set.
- New per-entry option `event_retention_days`: 0 (keep forever, default) or
  7–3650. A daily job removes archived events older than that, never clips.
- Layout (provider-neutral, reusable by other providers later):
  `<root>/events/<provider>/<camera>/<YYYY>/<MM>/<occurred_at>-<alarm_id>.json`
  and the picture next to it as `.jpg`. `<occurred_at>` is UTC
  `YYYYmmddTHHMMSSZ` so names sort by time. JSON (`schema_version: 1`):
  `provider`, `camera`, `alarm_id`, `occurred_at` (epoch s), `category`,
  `alarm_type`, `title`, `picture` (file name or null), `archived_at`. No
  serials, tokens or vendor URLs.
- Writer: the integration. Live alarms come from `EzvizAlarmListener` (it
  already receives every new alarm); at start and after a reconnect a
  backfill walks the bridge history with `before` until it meets an alarm
  already archived. Pictures come from the existing picture relay call
  (`client.ezviz_alarm_picture`). Writes reuse the `.partial` → fsync →
  rename pattern and the mount checks of `backup_storage.py`. Idempotent: an
  existing JSON for the same id is left as is.
- Mount unavailable → events are not dropped from the bridge (it still keeps
  N); the archiver retries on the next alarm and reports a repair-free warning
  sensor/state, never a crash.
- Reading: a new websocket
  `media_bridge/events/list` (`entry_id`, `page`, `page_size`, optional
  `day`) returns archived events newest first with a total, so the panel uses
  the same pager as the other archives with a known page count. Pictures go
  through a signed HA path like today's alarm pictures. Access (my call):
  listing and pictures follow `can_access_ezviz_entry`, exactly like live
  alarms; deleting archived events or clips is admin only.
- Panel: when `event_archive` is on, the events card lists the archive
  (complete history); otherwise it keeps the 0.47.0 behaviour (bridge
  history). Same access rule as today (`can_access_ezviz_entry`).
- Fix in the same slice: the network-archive inventory lists `ezviz` copies
  (regex and tests), so archived EZVIZ clips are playable from Vistoda.

### 3. Event modal (panel)

- Tapping a row opens a modal (the panel's existing dialog/modal pattern and
  accessibility rules: focus trap, Esc, labelled close, mobile full-screen):
  large picture, local time and date, category label and icon, title,
  previous/next event buttons (keyboard arrows too), and a "Video" section.
- Video section, first match wins:
  1. SceneTrove linked (section 4) → button "Apri in SceneTrove" (opens a new
     tab at the event instant).
  2. A Vistoda clip covers the instant (a bridge recording or a network
     archive copy whose start ≤ event ≤ end) → inline player using the
     existing signed playback path.
  3. Otherwise → "Salva dalla microSD", calling the existing `create_sd` for
     the window event − 10 s to event + 50 s (my call; within today's 120 s
     cap), then playing it when ready. The button says it wakes the camera.
- No video automation (non-goal).

Sections 4–8 (SceneTrove link, clip destination and shared archive, events
in SceneTrove, deletion, changing modes), constraints and phasing continue in
`2026-10-29-event-archive-and-scenetrove-link-design-part2.md`.
