# ADR 0013: In-place adoption of managed provider apps

## Status

Accepted.

## Context

Ring and EZVIZ originally ran as external private bridges. Installing their
Supervisor apps changes both the private hostname and workload credential. A
second config entry would duplicate devices and break the product's stable
identity contract; deleting and recreating the first entry would do the same.

## Decision

Supervisor discovery matches an existing Vistoda config entry by provider and
alias. After authenticating the new private endpoint, the flow updates that
entry in place with the managed-app URL, credential, title and URL-derived
unique ID. A changed loaded entry is reloaded once; an identical rediscovery is
an idempotent abort without a reload.

The operational cutover must restore the provider session before Home
Assistant consumes the managed discovery. This keeps the update atomic from
the integration's perspective. The old runtime remains available until native
health and entity acceptance gates pass.

## Consequences

- config-entry, device and entity IDs survive the topology change;
- dashboards, automations and Apple clients keep their existing references;
- restarting a managed app does not create another integration entry;
- provider plus alias is an explicit uniqueness boundary during adoption;
- rollback restores the prior entry data and external runtime from the
  pre-cutover backup.
