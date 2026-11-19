# ADR 0029: SceneTrove microSD sync schedule in the EZVIZ details page

- Status: accepted
- Date: 2026-11-19

## Context

SceneTrove copies an EZVIZ camera's microSD clips through the Vistoda EZVIZ
app on a per-device schedule (60 minutes by default). Every run wakes a
battery camera: on the front-door CP4 the hourly run roughly doubled the drain
(about 6 %/day without it, 10-12 %/day with it) and the battery went flat
twice. The owner wants to choose the interval in Vistoda, the household app,
not only in SceneTrove's device manager. Until now Vistoda knew SceneTrove only
as a browser link (`scenetrove_url`, `scenetrove_device`) and a shared folder;
ADR 0001 limits what a config entry stores to the bridge URL, its token and
the alias.

## Decision

- SceneTrove stays the single owner of the schedule: it stores it, validates
  it and runs the sync (SceneTrove ADR-0023). Vistoda never keeps a copy, so
  there is nothing to reconcile; a change made in either app is what both show.
- An EZVIZ entry linked to SceneTrove may also store a SceneTrove personal
  token, option `scenetrove_token`. It must be created by a SceneTrove
  administrator with only the `devices:sd-sync` scope, which grants
  `GET`/`PUT /api/devices/{device}/sd-sync` and nothing else. The options form
  field is a password field that is never pre-filled; leaving it empty keeps
  the saved token and clearing the SceneTrove address removes it. The token is
  used only by Home Assistant's backend: it is not part of panel metadata,
  WebSocket answers or diagnostics.
- Defence in depth on save: before the options flow stores a new token, or
  sends the saved one to a new SceneTrove address, it calls `GET /api/devices`
  with that token. Only `403` proves the token narrow and lets it be saved. A
  `200` means the token can read every device and is refused as too broad
  ("create one with only the microSD sync permission"); `401` is refused as
  not accepted (expired or revoked). Any other answer, a redirect, a timeout
  or an unreachable SceneTrove is refused as "could not verify" and the token
  is not stored: an unverified token is never kept, and the owner retries when
  SceneTrove is reachable. A `403` does not prove the token holds
  `devices:sd-sync`; a token that lacks it only makes the card show
  SceneTrove's refusal.
- Every SceneTrove call uses `allow_redirects=False`, so the bearer token is
  never resent to another location; a `3xx` answer is the error
  `scenetrove_redirected`.
- `media_bridge/ezviz/sd_sync/info` returns the schedule, availability, last
  run (result code, time, counts) and the next run to every user who may see
  the camera; upstream free-text messages are dropped.
  `media_bridge/ezviz/sd_sync/set` is for Home Assistant administrators only,
  accepts `enabled` plus 60, 180, 360, 720 or 1440 minutes, and is logged with
  the user. Turning the sync off accepts any interval SceneTrove accepts
  (15-1440) and the panel sends the current one back unchanged, so "off" never
  overwrites a custom interval set in SceneTrove. A `PUT` answering `404`
  while a `GET` of the same device works means a SceneTrove older than its
  ADR-0023 (the `PUT` falls through to the whole-device route): it is reported
  as `scenetrove_unsupported_version`, not as an unknown device. SceneTrove checks the request again (admin token, 15-1440 minutes,
  live source required to turn it on). Answers map to stable codes.
- The EZVIZ details page shows a "microSD sync with SceneTrove" card under the
  SceneTrove link card: Off, every 1, 3, 6, 12 or 24 hours, one line on the
  trade-off (more often: fresher recordings, more battery use), the battery
  recommendation (6 hours) when the camera reports a battery level, the last
  sync time and result, the last success and the next run. Without a token it
  explains how to add one; errors offer a retry.

## Consequences

- No redeploy is needed to change the interval: SceneTrove applies it at the
  next scheduler tick.
- A Home Assistant configuration backup now contains a narrow SceneTrove
  token: it can read and change the sync schedule of every SceneTrove device,
  nothing more. Revoking it in SceneTrove disables only this card.
- Mains cameras keep SceneTrove's 60-minute default; Vistoda recommends, but
  never silently applies, 6 hours for battery cameras.
- Turning the sync off removes the device's `scenetrove_sd_sync_enabled`
  series, so the staleness alert stays quiet for an intentionally disabled
  sync.
