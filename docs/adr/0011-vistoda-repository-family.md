# ADR 0011: Vistoda repository family

- Status: Accepted
- Date: 2026-08-23

## Context

The original repository names described implementation details rather than the
single product users configure in Home Assistant. Blink also lived inside the
deployment repository, which mixed product source with fleet orchestration.

## Decision

The product family uses `vistoda-home-assistant`, `vistoda-blink`,
`vistoda-ezviz`, `vistoda-ring` and `vistoda-apple` as canonical repository
names. Provider code owns its tests, releases and architecture records. Ansible
only pins, deploys and verifies immutable revisions.

Existing wire paths, the `media_bridge` and `blink_live_bridge` Home Assistant
domains, entity identifiers, executable names and container service names stay
stable. They are compatibility contracts, not user-facing product identities.
Changing one requires a separate migration ADR and a rollback-safe cutover.

## Consequences

Documentation and UI consistently describe Vistoda and its provider
connectors. Existing config entries and automations survive the repository
migration. Operational names may temporarily differ from the product label,
and that difference must be documented rather than hidden.
