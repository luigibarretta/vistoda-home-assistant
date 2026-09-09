# ADR 0022: Canonical nested Vistoda panel routes

- Status: Accepted
- Date: 2026-09-09
- Supersedes route selection in: [ADR 0014](0014-unified-provider-panel.md)

## Context

Home Assistant marks a sidebar panel as selected only when the first route
segment equals the registered panel URL. The hidden routes `/vistoda-ring`,
`/vistoda-blink` and `/vistoda-ezviz` therefore rendered the right Vistoda
component but left the visible `/vistoda` sidebar entry inactive.

Those legacy links already exist in device metadata and user bookmarks, so
removing them would break compatibility.

## Decision

Use `/vistoda/ring`, `/vistoda/blink` and `/vistoda/ezviz` as canonical provider
routes beneath the visible `/vistoda` panel. Resolve the provider from the
pathname and react to Home Assistant's `route` setter so navigation can reuse
one custom element.

Keep the former top-level provider panels registered as hidden compatibility
routes. When one loads, replace its history entry with the matching canonical
nested route and emit Home Assistant's normal location-change event. Preserve
the query string, including Ring answer and entry deep links.

## Consequences

- The Vistoda sidebar item remains active on every provider view.
- Existing links continue to open the same provider without a full page reload.
- New device configuration URLs and panel navigation use nested routes.
- Provider selection remains browser-local and receives no bridge address or
  credential.
