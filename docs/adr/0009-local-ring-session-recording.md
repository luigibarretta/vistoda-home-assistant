# ADR 0009: Local Ring session recording through Home Assistant

- Status: accepted
- Date: 2026-08-22
- Supersedes: ADR 0005 and the recording mechanism in ADR 0007

## Context

The owned Ring account does not expose Call Recording in the official app, so
an eligibility-gated provider import cannot meet the Vistoda contract. The
Vistoda panel already has the remote Ring track and owns microphone permission
during its authenticated browser communication.

## Decision

A small browser recorder mixes the remote stream with the microphone only while
the user has enabled it. Manual and globally persisted automatic recording use
the same lifecycle. Switching between listen and talk updates the local source
without ending the recording; session teardown finalizes and uploads before
the peer is destroyed.

The page sends at most 8 MiB of base64 through a Home Assistant WebSocket
command. The backend validates encoding and size, then forwards raw WebM or MP4
to the private Rust bridge with bounded start/end timestamps. Browser code
never receives the bridge token. Errors are redacted and create no partial
archive item.

The ding automation is now reserved for urgent incoming-call notifications on
each registered household Companion. It does not start media or recording in
the background, because a browser microphone requires an explicit user gesture.

## Consequences

- the misleading provider eligibility error and import service are removed;
- only communications actually routed through Vistoda can be recorded;
- the global switch remains server-side integration state, not local storage;
- the same archive remains consumable by Home Assistant and SceneTrove.
