# ADR 0007: Ring communication audit and global recording policy

- Status: accepted
- Date: 2026-08-22
- Supersedes: the recording UX scope in ADR 0005

## Context

Communication startup and teardown need user-visible audit plus ICE timing.
Automatic recording must be one integration policy, not browser-local state.

## Decision

The authenticated WebSocket boundary records every successful start and matched
end. It fires `vistoda_ring_communication_started` and
`vistoda_ring_communication_ended`, and adds concise Logbook entries. Payloads
contain a truncated SHA-256 session reference, mode, ICE duration, call duration,
bounded reason and bridge ACK; raw session UUIDs are never published.

The browser reports measured ICE gathering time. An eight-second timeout may
continue only if the local SDP already contains a candidate. Zero candidates
remains an explicit failure.

`Registra automaticamente` is a Home Assistant switch backed by config-entry
options. Every browser reads the same value and starts one official Ring Call
Recording import after communication becomes active. Manual import remains
available. The browser never captures or uploads conversation media itself.

## Consequences

- Logbook and automations can audit communication lifecycle safely;
- bridge Prometheus telemetry can be correlated by timing, not identifiers;
- the policy survives page refreshes and applies consistently to all users;
- official Call Recording eligibility and its spoken notice still apply.
