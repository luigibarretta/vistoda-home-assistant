# Reconnect accounts and configure network backups

Blink options include **Automatically back up Blink USB clips every hour**.
Enable it only after configuring writable network media storage. The Home
Assistant worker runs with the panel closed, creates at most 20 new copies per
pass and continues next hour. Each pass reads at most 100 pages of 50 clips.
It never deletes originals or propagates USB deletions. Diagnostics expose the
last pass under `usb_auto_backup`. The first pass runs at the worker's next
hourly interval; use **Back up archive** in the USB section for an immediate
copy. The local archive's backup button copies only Vistoda local recordings.

Blink recording controls are in live view's **REC** menu. The **HA local
archive** accordion retains local file management and playback. Blink chooses
its configured provider destination (USB when Local Storage is active).
HA-local capture supports 15, 30 or 60 seconds. Provider `save=false` discards
the whole session; it is not a stop-and-keep-segment operation. USB duration
controls therefore remain unavailable: saving follows the actual end of the
shared session, including any other viewers.

Use **Settings → Devices & services → Vistoda → Configure**, then select
**Reconnect account**. Managed Ring and EZVIZ entries also support Reconfigure
as a direct reconnect route. Confirm the provider and sign in to the same
vendor account. Complete its newest verification challenge if requested.

Home Assistant forwards account credentials to the existing private Vistoda
provider only for that enrollment request. It does not add passwords, account
names or OTP codes to the config entry. Reconnect preserves the config entry
ID, unique ID, title, options, physical Ring binding, entity IDs and history.
An incorrect or expired OTP returns to a fresh enrollment; it does not create
another entry. Reconnect does not approve a Ring alias changing physical device.

Ring Supervisor discovery supports one aggregate payload containing `devices`
with distinct aliases and string-valued numeric `device_id` values. Existing
entries are adopted only for the same endpoint and alias, retaining all stored
binding data. A changed known physical ID aborts adoption. New intercoms are
selected in the native setup flow; remaining aliases continue through further
setup after the first enrollment, without requesting another account password.
Legacy single-alias discovery remains supported.

After the first Ring enrollment, HA reads the authenticated `/v1/intercoms`
inventory and presents real intercom names and locations. The provider must
return a routable `alias` for each device; HA does not guess or configure Rust
aliases. For old providers without aliases, HA accepts a configured alias only
when a fresh status request confirms the exact physical `device_id`. A single
unbound bootstrap alias therefore works only after that provider binding is
verified; multi-device turnkey setup requires the provider's automatic aliases.
Reauthentication of an existing entry skips new-device selection and retains
its original physical binding.

EZVIZ camera and connectivity entity unique IDs now include the config entry
ID. Setup migrates legacy alias-only IDs in place, retaining entity IDs and user
names. A legacy device shared by multiple entries is split only for the current
entry; the other device and entities remain. Existing automations referencing
entity IDs continue to use those same IDs. Review device-based automations only
where a previously ambiguous shared device had to be separated.

For network backup, first add a writable **NFS or SMB network storage** in
**Settings → System → Storage** with usage **Media**. Then enter its storage name
in Vistoda's options for the Blink or EZVIZ entry. Enter `family_archive`, for
example, not an IP address, share URL or `/media/...` path. The compatible
default is `vistoda_archives`.

Each write verifies an exact writable NFS/NFS4/SMB mount under `/media`, rejects
local-directory and symlink substitutes, and requires at least 512 MiB free.
An absent network mount leaves backup unavailable; it never falls back to local
HA storage. Changing the configured storage name requires that destination to
be ready. An existing unavailable destination does not block account reconnect.
Configure Blink's storage once for both its local recordings and USB backups.

Provider recordings preserve their actual media type: MPEG-TS (`video/mp2t`)
uses `.ts`; MPEG-PS (`video/mpeg`) uses `.mpegps`. Blink USB clips remain `.mp4`.
Local recording backups verify the declared size and SHA-256 before committing
an atomic file plus metadata sidecar. A conflicting existing checksum is an
error and does not overwrite the existing file. EZVIZ manifests must match the
entry's camera alias.

Downloaded diagnostics expose `reauth_supported` and redacted `backup_storage`
readiness: ready, missing/not writable/unavailable mount, or low free space.
They omit storage/server paths, credentials and physical Ring bindings.

Regression checks: `python -m pytest -q tests/test_release_*.py`. These tests
execute the integration's flow, identity migration, mount detection, and backup
code using isolated HA framework doubles and temporary files. They do not
contact vendors, mount shares, reconnect production accounts or open entrances.
