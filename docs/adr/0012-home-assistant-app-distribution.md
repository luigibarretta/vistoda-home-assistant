# ADR 0012: Home Assistant app distribution

- Status: Accepted
- Date: 2026-08-23
- Supersedes: ADR 0003 for the default installation path

## Context

Remote provider bridges are operationally sound but asking Home Assistant users
for an endpoint, port and workload token exposes deployment details. Blink also
required separate YAML despite already running as a Supervisor app.

## Decision

Vistoda uses one public HACS integration family and one `vistoda-addons` store
containing separate Blink, EZVIZ and Ring apps. Each app generates its private
workload credential, keeps its listener inside the Supervisor network and sends
a `hassio` discovery message containing the provider connection.

The config flow asks only for provider account credentials, MFA and necessary
device identity. Explicit URL/token setup remains available as an advanced
external-backend mode for Home Assistant Container, SceneTrove and native
clients. Provider Rust cores are not forked for Home Assistant packaging.

## Consequences

Ordinary users install the integration, add one app repository and select the
providers they need. Managed entries cannot edit bridge connection fields.
Release gates require public `amd64` and `aarch64` images matching store
versions. Home Assistant restarts no longer depend on a separate homelab host,
while remote deployments retain their current contracts.

