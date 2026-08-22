# ADR 0005: Ring recording import

- Status: superseded by ADR 0009
- Date: 2026-08-15
- Supersedes: the two-start-button UX and no-recording scope in ADR 0004

## Context

A Ring Intercom ding may be answered from Vistoda or the official Ring app.
Starting an independent WebRTC session at ding time would compete with that
call, fail to capture the app user's outbound audio and bypass Ring's official
recording notice. Home Assistant already exposes `event.citofono_ding` through
the supported Ring integration.

Ring's official Call Recording feature starts after a call is answered, stores
audio for Ring Intercom Audio and plays a spoken notice before recording. It
may require an eligible subscription and an explicit Privacy Settings toggle.

## Decision

Vistoda exposes `media_bridge.import_ring_recording`, accepting only the Unix
timestamp of a recent ding. An as-code Home Assistant automation calls it from
`event.citofono_ding`. The backend forwards the timestamp to the private bridge
without vendor credentials, event identifiers or media URLs.

The bridge waits 15 seconds before vendor access, then polls bounded metadata
for at most three minutes. It imports only a completed `audio_ready` or `ready`
event whose timestamp matches the ding. Repeated triggers within five seconds
reuse the same job or recording. Missing eligibility returns an explicit
unavailable state; Vistoda never enables the provider setting itself and never
falls back to covert WebRTC capture.

Completed MP4 media is committed atomically under a private `0700` directory
with `0600` files. The archive retains 30 days and at most 512 MiB. Its REST
contract requires the bridge bearer token for list, media and idempotent
delete. Home Assistant exposes only count, timestamps and byte sizes through
authenticated integration boundaries.

The Ring panel now starts one listen-only session. Its microphone toggle uses
`replaceTrack`: activation requests browser permission; deactivation replaces
the microphone with silence and stops the captured track. This preserves one
peer connection and makes microphone state unambiguous.

## Consequences

- app-originated and Vistoda-originated answered calls share one official
  recording source and Ring's notice;
- a missed or unrecorded call expires without creating a local file;
- service execution is asynchronous and does not block Home Assistant while
  Ring finalizes media;
- SceneTrove can consume the authenticated archive and acknowledge it through
  idempotent delete without learning Ring credentials.
