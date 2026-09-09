# 0021: Multiple Ring entries and explicit list management

Status: Accepted

## Context

The Ring panel selected the first config entry returned by Home Assistant even
though the backend commands were already scoped by `entry_id`. The door service
also rejected every configuration except exactly one loaded Ring bridge. This
made a second apartment intercom ambiguous and unsafe to operate.

Recording lists could be created and deleted only indirectly through the active
archive filter. Their persisted model had no rename operation and the interface
did not provide an inventory of lists.

## Decision

- Return every Ring entry in a stable order and include its non-secret alias.
- Show an intercom selector only when more than one entry exists. Prefer the
  exact `entry` query parameter, then the browser's saved choice, then the first
  available entry.
- Destroy any active audio session and reset entry-scoped archive state before
  switching the selected intercom.
- Carry `entry_id` in call acknowledgement and Ring event context so incoming
  notification deep links can select the originating intercom.
- Keep `media_bridge.open_ring_door` backward compatible for one entry. Require
  an explicit `entry_id` when several bridges are loaded and fail closed if the
  requested entry does not exist.
- Provide a visible recording-list manager. Renaming preserves memberships;
  deleting a list never deletes recording media.

## Consequences

One-intercom installations keep the compact interface and existing service
calls. Multi-intercom installations gain deterministic selection without
sharing audio, controls, recordings or list state across config entries. The
official Ring fallback still fails closed when Home Assistant cannot resolve a
single safe source entity.
