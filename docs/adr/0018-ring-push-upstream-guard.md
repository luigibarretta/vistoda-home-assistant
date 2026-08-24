# ADR 0018: Temporary upstream Ring push guard

## Status

Accepted and temporary.

## Context

Home Assistant's official Ring listener can terminate when a Web Push crypto
key or salt omits base64url padding. A second sender variant appends another
parameter to `Crypto-Key`; positional parsing then retains unrelated data.
Upstream fixes are proposed but are not released in the dependency bundled by
Home Assistant Core 2026.8.3. When the listener terminates, the official ding
event no longer provides a dependable incoming-call trigger.

## Decision

Vistoda installs a narrow process-local guard before config entries load. It
selects `dh` and `salt` by name, restores base64url padding, and skips one
malformed encrypted payload instead of allowing it to terminate the FCM read
loop. It never logs payloads, keys or credentials.

The guard is idempotent, activates only when the affected third-party class is
installed, and stays disabled once the dependency exposes its upstream named
header parser. It does not vendor or modify Home Assistant site packages.

## Consequences

- Ring ding delivery survives the observed malformed or unpadded payload.
- The official Ring integration remains the realtime event owner.
- The workaround must be removed after the upstream fix is released and proven
  on the deployed Home Assistant version.
- A malformed individual push can be skipped; later valid pushes continue.

## Upstream references

- `sdb9696/firebase-messaging#37`: padded decoding and fail-local handling.
- `sdb9696/firebase-messaging#43`: named Web Push header parameter parsing.
- `home-assistant/core#173915`: Ring ding listener termination in HAOS.
