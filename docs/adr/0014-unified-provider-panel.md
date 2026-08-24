# ADR 0014: Unified provider panel

- Status: Accepted
- Date: 2026-08-24

## Context

Vistoda exposed Ring through `/vistoda-ring`, while Blink and EZVIZ were native
Home Assistant entities without equivalent first-party pages. This made one
product appear as unrelated integrations and encouraged provider UI to grow
inside a Ring-specific module.

The direct Ring route is already used by Home Assistant device links,
notifications and the Apple companion. It cannot disappear during a UI
consolidation. Camera rendering must also remain inside Home Assistant's
authenticated media boundary; the browser must never receive bridge URLs or
workload tokens.

## Decision

Register one sidebar entry at `/vistoda` as the product hub. Register
`/vistoda-ring`, `/vistoda-blink` and `/vistoda-ezviz` as hidden direct routes.
All routes load the same versioned web component and select a provider through
fixed panel configuration. `/vistoda-ring?answer=1` remains compatible.

An authenticated `media_bridge/panel/info` WebSocket command supplies a
bounded, secret-free inventory of enabled entities grouped by provider and
device. Provider views use normal Home Assistant state, service and more-info
contracts. Snapshot refresh and cloud-affecting operations remain explicit
user actions.

Ring keeps full-duplex communication, local recording and controls. Blink gets
system arming, camera navigation, snapshot refresh, motion and native live
opening. EZVIZ gets snapshot and native live opening while SceneTrove remains
the owner of recording ingest and spool acknowledgement.

## Consequences

- Home Assistant shows one Vistoda sidebar item instead of a provider-specific
  item.
- Existing provider deep links remain stable and can be used as device
  configuration URLs.
- New provider pages must use the shared shell, styles and inventory contract;
  provider-specific logic stays in bounded modules under the LOC gate.
- The inventory command intentionally excludes endpoints, tokens, unique IDs
  and disabled entities and caps output per provider.
