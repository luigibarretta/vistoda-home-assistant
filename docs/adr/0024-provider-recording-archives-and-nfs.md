# ADR 0024: Provider recording archives and NFS backup

- Status: accepted; Blink USB mutation boundary superseded by ADR 0025
- Date: 2026-09-09

## Context

The Blink panel's former record action invoked a cloud command that failed and
could produce a misleading motion notification. EZVIZ finite capture existed
for SceneTrove but was not available as a standalone Vistoda workflow. Users
also need durable NAS copies without filling the Home Assistant system disk.

Blink Sync Module USB, EZVIZ microSD and bidirectional audio are separate vendor
protocols. An official-app screen or discovered URL does not prove a safe
read/write contract.

## Decision

Both provider apps expose backend-paginated recording inventories and fixed 15,
30 or 60 second live captures. Vistoda scopes them to the selected camera and
offers authenticated download and confirmed local deletion. Blink captures
MPEG-TS; EZVIZ captures MPEG-PS and remuxes it on demand to fragmented MP4 for
browser playback without persisting a duplicate. SceneTrove remains independent.

An administrator may copy one item or the complete ready inventory to
`/media/vistoda_archives`. Home Assistant streams the provider response without
placing a token in the browser, enforces a 256 MiB receive ceiling, compares
declared bytes and SHA-256, fsyncs a private partial and publishes it atomically
with a redacted JSON sidecar. Existing files count only when their checksum
matches. The operation is serialized and leaves local provider media intact.

The Blink Sync Module inventory is separately paginated by the provider app.
Vistoda plays or downloads its MP4 clips through signed HA paths and can copy a
single clip or traverse all backend pages for NFS backup. Because Blink does not
publish a checksum, HA computes one while streaming and records it in the
sidecar before atomic commit. At the time of this decision no command
acknowledged, deleted or mutated the provider-owned USB object. ADR 0025 later
added separately guarded deletion and compatible-media formatting.

Backup fails closed unless `/proc/self/mounts` identifies the exact path as NFS
and 512 MiB of headroom remains. A production installation provisions and
limits that storage outside Vistoda through the Home Assistant Supervisor. This
prevents an “active” storage entry or local substitute from silently filling
the Home Assistant disk.

Direct provider recording to USB/microSD and Blink/EZVIZ talk remain gated until their exact
model-specific list, transport, mutation and recovery contracts pass live
canaries. No UI control may imply parity merely because downstream media works.

## Consequences

- Recording from Vistoda no longer invokes Blink motion recording.
- The NAS copy is independently durable and does not consume provider quota.
- Local delete never cascades into NFS, SceneTrove, USB or microSD storage.
- Direct recording to provider storage remains gated. Later guarded Blink USB
  management is defined by ADR 0025.
