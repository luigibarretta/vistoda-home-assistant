# ADR 0020: Mobile Ring archive and recording lists

- Status: accepted
- Date: 2026-09-09

## Context

The Ring archive exposed only a wide table. It remained usable through
horizontal scrolling, but that interaction was a poor default on a phone. The
panel also had no durable way to group important recordings, and the mobile
Vistoda subtitle was constrained to one line beside the refresh action.

## Decision

The archive has two equivalent presentations. A viewport up to 620 px starts
with cards; wider viewports start with rows. An explicit Cards/Table choice is
stored locally in the browser so the same user can override the responsive
default without changing another client's preference. Date, duration, size,
playback, file information, list assignment and confirmed deletion remain
available in both presentations.

Custom lists are many-to-many metadata owned by the Home Assistant integration.
They are stored through the supported private, atomic `Store` API and scoped to
the Ring config-entry ID. Authenticated WebSocket commands create and delete
lists and set membership. Names, identifiers, list counts and memberships are
bounded; adding a recording verifies that the media still exists. Loading the
archive prunes orphan memberships, while successful media deletion removes its
memberships immediately. Deleting a list never deletes a recording.

The mobile panel header reserves space for the refresh control and lets the
subtitle wrap in the remaining column. The back and refresh actions retain
44-pixel touch targets.

## Consequences

Lists are shared by authenticated Home Assistant clients and survive Core
restart, while the visual preference remains intentionally device-local. No
recording bytes, provider credential, bridge URL or bearer token enter the
metadata store. The Rust Ring archive format and retention policy do not
change.
