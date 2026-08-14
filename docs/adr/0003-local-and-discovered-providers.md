# ADR-0003: Local and discovered provider adapters

## Context

EZVIZ and Ring own standalone Rust runtimes, while Blink Live Bridge must run
inside Home Assistant to reuse the single loaded Blink coordinator and avoid a
second vendor login. Presenting every provider as a remote URL would either
duplicate Blink sessions or hide it from the shared Vistoda experience.

## Decision

Vistoda supports two adapter classes:

- remote EZVIZ and Ring bridges, discovered through `_vistoda._tcp.local.` and
  authenticated with a dedicated API token that is never advertised;
- a local Blink adapter, discovered by the loaded Blink Live Bridge and adopted
  without URL, token, vendor credentials or new camera entities.

The existing Blink API and camera entities remain owned by Blink Live Bridge so
SceneTrove URLs and dashboard references stay compatible. Vistoda adds only its
provider-level connectivity device.

## Consequences

- one Vistoda setup surface covers all three providers;
- Blink keeps exactly one vendor session and one set of live camera entities;
- remote discovery leaks only endpoint, provider, alias and version metadata;
- manual remote setup remains available when multicast is unavailable;
- Ring media stays absent until its separate protocol canaries pass.
