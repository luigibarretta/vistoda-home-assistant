# ADR 0016: Version the complete panel asset graph

## Status

Accepted.

## Context

The Vistoda panel is an ES module graph. Adding a release query to only the
entry module does not change the URLs of its relative imports, so a browser can
continue using older provider views after a Home Assistant upgrade.

## Decision

Serve every panel release below `/vistoda_static/<integration-version>/` and
register the panel entry point from that versioned directory. Relative imports
then inherit the release path and the complete module graph receives new URLs.

Keep Home Assistant static cache headers disabled as a secondary safeguard.

## Consequences

- Opening or reloading Vistoda after an upgrade loads one coherent release.
- Users do not need a hard refresh to receive provider UI changes.
- The static route changes only when the integration version changes.
- Core must restart when a new integration release is deployed, as already
  required by the managed deployment contract.
