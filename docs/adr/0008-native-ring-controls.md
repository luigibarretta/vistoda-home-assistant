# ADR 0008: Native Ring controls with explicit delegation rollback

- Status: accepted
- Date: 2026-08-22
- Supersedes: the single cloud-owner decision in ADR 0006

## Context

Vistoda must eventually replace the official Ring integration while retaining a
safe rollout and stable entity IDs for existing dashboards and automations.

## Decision

Vistoda's button, three number entities, battery and last-activity sensors keep
their stable IDs. In native mode they use the Rust bridge's shared status and
control API. A single 60-second coordinator supplies battery, online state,
volumes and last activity to avoid duplicate provider calls.

`Delega a Ring ufficiale` is a config-entry option exposed as a global switch.
It is available only when every required official control entity resolves
unambiguously. ON routes portone and volume writes to those entities; OFF routes
them through Rust. Missing official controls force native mode. Battery and last
activity follow the selected source. Ding and unlock events remain delegated
until native push events pass an independent canary.

Unlock is always a single request. Automated production canaries may write each
current volume back unchanged, but must never open the door.

## Consequences

- dashboards and automations do not change entity IDs during migration;
- Vistoda works natively for status, battery, volumes and unlock;
- official control integration is a visible, removable rollback dependency;
- full replacement still requires native ding/unlock push-event acceptance.
