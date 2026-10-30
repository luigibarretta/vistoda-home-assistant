# ADR 0028: EZVIZ event archive on network storage and the event modal

- Status: accepted
- Date: 2026-10-30

## Context

The Vistoda EZVIZ app keeps a bounded alarm history (200 per camera by
default, up to 2000 since app 0.17.0) on Home Assistant's own disk. Users who
want the answer to "who came to the door while I was out?" over weeks need a
longer history that does not grow Home Assistant backups, and a way to see an
event with its video. Design:
`docs/superpowers/specs/2026-10-29-event-archive-and-scenetrove-link-design.md`.

## Decision

- EZVIZ entries gain two options: `event_archive` (off by default, needs a
  ready network storage) and `event_retention_days` (0 = forever, or 7–3650).
- Events are stored provider-neutrally under
  `<storage>/events/<provider>/<camera>/<YYYY>/<MM>/<UTC stamp>-<alarm_id>.json`
  with the picture as `.jpg`; writes are atomic and idempotent, reads never
  follow symlinks and skip foreign or oversized files. Retention deletes
  event files only, never clips.
- The archiver follows the alarms the listener already publishes, backfills
  the app history newest first with `before` pages until an alarm is already
  archived, and reports a missing mount once per outage without blocking
  alarms. Options are read live; history before enabling is backfilled at the
  next start.
- `media_bridge/events/list` and `/api/media_bridge/events/{entry}/{event}.jpg`
  follow the same camera access rule as live alarms.
- The panel's events card pages the archive on the server when enabled, else
  the app history. Each event opens a modal: picture, time, category, title,
  previous/next, and the video — a ready recording covering the instant, or
  saving event − 10 s to + 50 s from the microSD (it wakes the camera).
- EZVIZ copies in the network archive (`ezviz/<camera>/<id>.mpegps|.ts`) are
  now listed; they are download-only because browsers cannot play them.

## Consequences

No clip is saved automatically per event: every microSD playback wakes a
battery camera. The SceneTrove link, shared archive and deletion are later
phases of the same design.
