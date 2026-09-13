# ADR 0027: Mobile archives, Blink settings backups and provider themes

- Status: accepted
- Date: 2026-09-13

## Context

Permanent checkbox columns and native page-size selects wasted space in mobile
archives. Blink camera settings also lacked a versioned recovery path, while
provider-branded colors were useful but could not replace Vistoda's neutral
default without user choice.

## Decision

Ring, Blink and EZVIZ share a segmented 10/25/50/100 page-size control. Mobile
cards enter selection through a visible button or a bounded long press; dragging
can extend the selection and ordinary vertical scrolling cancels before the
gesture arms. The total and selected counts stay visible.

Blink exposes named, bounded all-camera setting backups through an administrator-
only Home Assistant boundary. The provider serial and camera ID identify targets.
Restore creates a rollback backup, preflights every field and uses optimistic
revision checks. It refuses an alias-only mismatch, a concurrent update, a field
that is no longer writable and any transition to or from an uninitialized
temperature threshold. The backend accepts an optional camera subset for future
clients; the current panel intentionally restores the whole saved set.

The panel keeps the Vistoda palette by default. A persisted selector can enable
provider-specific colors for Ring, Blink or EZVIZ. Semantics and accessible names
do not depend on color.

Sync Module firmware, connection and storage used are informational. Wi-Fi
migration, eject and module removal are shown as unavailable controls and have no
provider action until their complete recovery flows are verified.

## Consequences

- Archive selection remains compact without becoming gesture-only.
- A restore never claims success for a setting it cannot reproduce exactly.
- Concurrent provider/app changes win instead of being overwritten by rollback.
- Destructive Sync Module administration is not implied by read-only metadata.
