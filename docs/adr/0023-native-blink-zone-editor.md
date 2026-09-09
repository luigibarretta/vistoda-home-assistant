# ADR 0023: Verified native Blink v1 zone editor

Status: accepted

## Context

Blink activity and privacy zones are not exposed by Home Assistant entities.
The official Android 59.1 client and the enrolled default cameras agree on the
v1 provider shape: 25 basic masks, each containing 12 micro-zone bits, for a
20×15 grid. Privacy areas are at most two integer `x`, `y`, `w`, `h` spans over
the same grid. The enrolled Owl/Mini advertises a different version but its v2
route rejects the request, so a translation cannot be verified.

## Decision

Vistoda renders one authenticated touch editor for verified v1 cameras. The
browser receives only normalized masks, spans and an opaque full-response
revision. It never receives bridge credentials or an untyped provider response.

Writes are administrator-only and submit the complete normalized draft. The
Rust provider validates exact dimensions and bounds, limits privacy spans to
two, clears activity bits under privacy, and rejects an entirely disabled grid.
Under the shared settings lock it rereads and compares the revision, posts the
native v1 body, rereads the result and restores the original body if verification
fails. Unrelated provider bits are preserved.

Owl/Mini v2 stays unavailable until a real enrolled model accepts a documented
schema and passes the same reversible canary. The UI must describe this as
unsupported, never as an empty or successfully reset grid.

## Consequences

- Default/Catalina users can manage activity and privacy zones without the
  official app.
- Concurrent or stale edits fail with a conflict instead of overwriting state.
- A successful HTTP response alone never counts as a committed zone change.
- Future zone versions require a separate typed adapter and live canary.
