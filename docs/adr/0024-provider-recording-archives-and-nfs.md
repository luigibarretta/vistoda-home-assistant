# ADR 0024: Provider recording archives and NFS backup

- Status: accepted
- Date: 2026-09-09

## Context

The Blink panel's former record action invoked a cloud command that failed and
could produce a misleading motion notification. EZVIZ finite capture existed
for SceneTrove but was not available as a standalone Vistoda workflow. The user
also needs durable NAS copies without risking the 30.8 GiB HAOS filesystem.

Blink Sync Module USB, EZVIZ microSD and bidirectional audio are separate vendor
protocols. An official-app screen or discovered URL does not prove a safe
read/write contract.

## Decision

Both provider apps expose bounded recording inventories and fixed 15, 30 or 60
second live captures. Vistoda scopes them to the selected camera and offers
authenticated download and confirmed local deletion. Blink captures MPEG-TS;
EZVIZ captures MPEG-PS. SceneTrove remains independent.

An administrator may copy one item or the complete ready inventory to
`/media/vistoda_archives`. Home Assistant streams the provider response without
placing a token in the browser, enforces a 256 MiB receive ceiling, compares
declared bytes and SHA-256, fsyncs a private partial and publishes it atomically
with a redacted JSON sidecar. Existing files count only when their checksum
matches. The operation is serialized and leaves local provider media intact.

Backup fails closed unless `/proc/self/mounts` identifies the exact path as NFS
and 512 MiB of headroom remains. Production provisions the path through
Supervisor, backed by a compressed 20 GiB ZFS child dataset exported only to
iot-01 with all identities squashed. This prevents an “active” Supervisor entry
or local directory from silently filling the VM.

Vendor USB/microSD controls and Blink/EZVIZ talk remain hidden until their exact
model-specific list, transport, mutation and recovery contracts pass live
canaries. No UI control may imply parity merely because downstream media works.

## Consequences

- Recording from Vistoda no longer invokes Blink motion recording.
- The NAS copy is independently durable and does not consume provider quota.
- Local delete never cascades into NFS, SceneTrove, USB or microSD storage.
- Arbitrary stop and vendor-media management remain roadmap items, explicitly
  gated by durable cancellation and provider protocol evidence.
