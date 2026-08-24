# ADR 0019: Selectable Ring recording storage

- Status: accepted
- Date: 2026-08-24

## Context

The Ring panel could manage local recordings but did not disclose their
location. The managed app also fixed every archive to private app data, even
when a user preferred Home Assistant media, share, or public app-config storage.

## Decision

Home Assistant consumes the Rust bridge's authenticated storage descriptor and
exact per-item display paths. It validates bounded absolute paths, rejects
traversal and requires every listed item to remain below the declared directory.
No bridge URL, bearer or provider credential crosses the WebSocket boundary.

The archive header shows the directory once. Repeating the full path as a table
column would make the mobile table needlessly wide, so each row has an accessible
Info action that reveals the exact path and offers clipboard copy. Private
storage is labelled explicitly and directs the user to Vistoda Ring app
configuration for destination changes.

Older external bridges without storage metadata remain readable; their panel
states that the path is unavailable until the bridge is upgraded.

## Consequences

The path displayed by the panel is runtime evidence, not a browser-derived
guess. Storage selection remains an app concern, while Home Assistant owns
authenticated presentation and validation.
