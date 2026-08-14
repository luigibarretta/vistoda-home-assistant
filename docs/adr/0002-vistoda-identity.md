# ADR-0002: Vistoda identity and stable domain

## Context

The original “Media Bridge” label described an implementation category but did
not give the Home Assistant integration a distinct product identity. Renaming
the integration domain would invalidate config entries and could change entity
identifiers and automation references.

## Decision

The user-facing product is named **Vistoda**, a fusion of *vista* and *custodia*.
The name covers the shared Home Assistant control plane while EZVIZ and Ring
protocol runtimes remain independent Rust repositories and deployments.

The manifest, HACS metadata, translations, config-entry titles and device labels
use Vistoda. The repository name and internal Home Assistant domain remain
`home-assistant-media-bridge` and `media_bridge` respectively. They are stable
technical identifiers, not user-facing branding.

Provider account secrets remain owned by their bridge. The Vistoda setup flow
must explain the origin and purpose of every requested value and distinguish
bridge authentication from vendor authentication.

## Consequences

- existing config entries and entity unique IDs require no migration;
- users can find the integration as Vistoda in Home Assistant;
- operational paths and SHA-pinned automation remain compatible;
- future providers can share the identity without sharing protocol code;
- all localized setup forms must keep field-level guidance complete.
