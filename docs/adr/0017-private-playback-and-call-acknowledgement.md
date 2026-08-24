# ADR 0017: Private playback and coordinated incoming-call acknowledgement

## Status

Accepted.

## Context

Saved Ring recordings exposed metadata and deletion but no authenticated media
path for browser playback. Incoming-call notifications opened Vistoda, but the
other household Companions could not know when one client had established the
audio session.

## Decision

Home Assistant reads at most 8 MiB from the private Rust recording endpoint and
returns it only through an authenticated WebSocket command. The panel creates a
short-lived browser Blob URL, exposes native audio controls plus explicit
ten-second backward/forward actions, and revokes that URL on replacement or
disconnect.

Every notification receives the Home Assistant automation context ID. The Ring
view accepts only a bounded call ID in its deep link and acknowledges it through
an authenticated WebSocket command only after WebRTC reaches the active phase.
Home Assistant emits `vistoda_ring_call_answered`; the automation that owns that
ID then clears the same tagged notification from all household Companions.

The official Ring integration remains the ding-event source until Vistoda gains
native push parity. Companion critical notifications are alerts rather than
CallKit or Android Telecom calls; platform delivery and dismissal limitations
still apply.

## Consequences

- Recordings remain private and seekable without exposing bridge credentials.
- Only one recording is materialized in browser memory at a time.
- Failed or competing sessions do not silence the other devices.
- The first active session dismisses every matching Companion notification.
- A two-minute timeout clears stale alerts even when nobody answers.
