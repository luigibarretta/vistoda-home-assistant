# Event archive and the SceneTrove link — part 2

Continues `2026-10-29-event-archive-and-scenetrove-link-design.md` (intent,
goals, anti-goals, current state and sections 1–3). Same status and owner.

### 4. SceneTrove link (integration + panel + SceneTrove)

- Per-entry options `scenetrove_url` (https URL, validated, no credentials
  or query string accepted) and `scenetrove_device` (SceneTrove device
  folder name; default: the camera alias).
- Panel presence: an info card in the camera's settings area explaining in
  two sentences what SceneTrove is (timeline and clips over time) with a link
  to its project page, and the field to set the URL. Shown until a URL is set;
  dismissible per user (stored in browser local storage, my call).
- Deep link built by the panel, no token:
  `<scenetrove_url>/?device=<device>&at=<ISO-8601 UTC instant>`. The browser
  session (SceneTrove login or the proxy in front of it) authorises.
- SceneTrove change: the app route accepts `at`; it opens that device's day
  and positions the timeline on the clip covering the instant, or the nearest
  clip after it with a short notice "nessuna clip in questo momento" when
  none covers it. Generic wording only (brand gate).

### 5. Clip destination and shared archive

Per-entry option `clip_destination`, visible only with `scenetrove_url` set.
A third "SceneTrove" destination was dropped (Luigi, 2026-10-29): SceneTrove
only pulls recordings it started itself, and the shared archive already gives
one copy visible in both apps.

- `vistoda` (default): today's behaviour; clips stay in the bridge and are
  copied to the Vistoda network archive.
- `shared`: one folder on the network storage used by both apps:
  - Vistoda writes clips for this camera to `<root>/shared/<device>/` with
    SceneTrove-compatible names `hiv<YYYYmmddTHHMMSS>Z-<id>.<ext>` plus the
    usual `.json` sidecar, and events to `<root>/shared/<device>/_events/…`
    with the section 2 format.
  - SceneTrove gets that folder as the device folder
    (`/data/sd/<device>` mounted from the same share). Mounting is
    deployment work, documented for users and done in homelab-ansible for
    Luigi's install.
  - SceneTrove indexes the clips in place (no copy) and reads `_events/` to
    show markers on its timeline (section 6).
  - SceneTrove keeps its own syncs for that device (cloud microSD sync,
    "Registra ora" captures) and they write into the same shared folder
    (`_captures/`, `_imports/…`), so the share is mounted read-write in
    SceneTrove. One folder, one copy, both apps see everything (my call:
    the user keeps SceneTrove's automatic microSD sync).
  - A clip saved from Vistoda in `shared` mode is copied automatically to the
    shared folder when the bridge recording completes, verified by SHA-256,
    and then the bridge copy is deleted (existing recording acknowledge/delete
    endpoint), so `/data` keeps no duplicate (my call).
  - In `vistoda` mode the copy to the network archive stays the existing
    manual admin action; nothing changes there (my call).

### 6. Events in SceneTrove

- SceneTrove reads `<device>/_events/<YYYY>/<MM>/*.json` (+ `.jpg`) as
  generic camera events: time, category, title, picture. Unknown categories
  show as "evento".
- Timeline: a marker per event on the day view; tapping it shows the picture
  and jumps to the clip covering the instant. Read-only: SceneTrove never
  writes or deletes in `_events/`.
- Index refresh follows SceneTrove's existing folder freshness/rescan, not a
  new watcher.

### 7. Deletion

- Vistoda gains "delete" for archived events and archived clips (admin only,
  per item and bulk, matching existing archive selection UI). Scope (my
  call): in `vistoda` mode it deletes the network-archive copy (the bridge
  copy keeps its own existing delete); in `shared` mode it can delete any
  clip in the shared device folder, including files SceneTrove wrote there
  (`_captures/`, `_imports/…`), because they are the same single copy both
  apps show.
- In `shared` mode the file is the same for both apps. The confirmation says
  so explicitly, e.g. "La clip verrà eliminata anche da SceneTrove." (Luigi,
  2026-10-29: deleting removes it for both, with a clear warning.)
- SceneTrove notices removals on its next rescan; it has no delete of its own
  in this design.
- Retention (`event_retention_days`) deletes only event JSON/JPEG, never
  clips.

### 8. Changing modes and existing files

My call: no migration. Existing files stay where they are; new writes go to
the location of the current mode. The event list and the "a clip covers the
instant" lookup search both `events/<provider>/<camera>/` and
`shared/<device>/_events/` (and both clip locations) and de-duplicate by
`alarm_id` / SHA-256. In `shared` mode events are written only to
`_events/`.

## Constraints

- Every repository's local CI gate (`ci-local`), LOC budgets (250 lines per
  maintained file in the Vistoda repos), tests per behaviour, IT and EN copy
  for every user-facing string in the panel and options.
- `scenetrove` brand gate: no vendor names anywhere in that repo.
- Heavy builds on dev-01 run one at a time through the build lock.
- Bridge API changes bump OpenAPI; integration keeps working with older
  bridges (feature off or degraded, never broken).
- Releases follow the existing chain: bridge tag → image → `vistoda-addons`
  catalog with signed release evidence → homelab pins → `deploy-ha-media-bridge`.

## Phasing (my call)

1. Bridge retention option + disclaimers (vistoda-ezviz, vistoda-addons).
2. Vistoda event archive, `media_bridge/events/list`, EZVIZ inventory fix,
   event modal with video rules 2–3 (integration).
3. SceneTrove link: options, info card, deep link, SceneTrove `at` route,
   modal rule 1.
4. Clip destination and shared archive, SceneTrove `_events/` markers,
   deletion with the shared-file warning; homelab mounts for Luigi's install.

Each phase ships on its own and leaves the system usable.

## Left to the builder

- Exact modal component structure and styling within the panel's patterns.
- How the archiver schedules backfill and retention (HA async tasks).
- The SceneTrove internal model for events (table vs. index file), as long as
  `_events/` stays the read-only source.
- Test fixtures and canary steps for each phase.
