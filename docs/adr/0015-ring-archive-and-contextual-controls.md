# ADR 0015: Ring archive management and contextual controls

- Status: Accepted
- Date: 2026-08-24

## Context

The first Ring panel exposed separate start and stop actions even though they
were mutually exclusive. Its archive showed only a count and newest timestamp,
so locally recorded calls could not be inspected or removed from Home
Assistant. Provider credentials must remain server-side, and destructive
actions need explicit intent and bounded behavior.

## Decision

Use one contextual call action. It shows start while idle, a disabled progress
state during negotiation, and terminate only for an established session. The
microphone action exists only while the same session is active. Compact buttons
retain visible labels, icons and accessible names.

Render local recordings in a client-paginated table with eight rows per page,
sorted newest first. Each row shows local date, duration and bounded size. A
row delete and a global delete-all action require confirmation. Home Assistant
exposes authenticated WebSocket delete commands and calls the Rust bridge's
idempotent `DELETE /v1/devices/{alias}/recordings/{id}` contract; browser code
never receives the bridge endpoint or bearer. Bulk deletion enumerates the
bounded inventory, continues after individual failures and reports exact
deleted and failed counts.

The portone action changes its lock icon only to show command progress and
acknowledgement. A successful service call is described as “command sent”; it
is not presented as proof that the physical door opened.

## Consequences

- mutually exclusive actions no longer compete for space;
- archive deletion is explicit, authenticated and idempotent;
- a partial bulk failure remains visible and can be retried safely;
- pagination and formatting live in a pure module with browser-independent
  tests, while every maintained file remains below 250 physical lines.
