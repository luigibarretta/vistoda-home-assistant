# Reconnect accounts and configure network backups

The hourly Blink network backup is switched on in the **NFS backup** tab
(**Hourly automatic backup to NFS**, administrators only) or in the Blink
options. Enable it only after configuring writable network media storage. The
Home Assistant worker runs with the panel closed and copies both Blink USB
clips and Blink **Local HA** recordings, including motion recordings. It
creates at most 20 new copies per pass across both sources and continues next
hour; each source reads at most 100 pages of 50 items per pass. Existing copies
are verified by checksum, not downloaded again. It never deletes originals or
propagates deletions. Diagnostics expose the last pass under `usb_auto_backup`.
The first pass runs at the worker's next hourly interval; use **Back up
archive** in the USB section for an immediate USB copy.

Without a Sync Module USB drive, the **Local HA** tab can record motion: an
administrator enables **Motion recording** (15/30/60 s, selected cameras).
Recording starts after Blink reports the event on an armed network, so it
captures the scene that follows, and each recording wakes the camera (battery
cameras drain faster). Motion recordings are a rolling buffer; manual
recordings are never removed automatically.

Blink's **Recording archive** is separate from the camera carousel. Its tabs
are **Blink USB**, **Local HA** and **NFS backup**. Changing camera does not
change the archive filter. USB can be filtered by Sync Module and camera;
Local HA and NFS have their own camera filters and page-size selectors.
NFS lists completed files with metadata on the configured mount, not pending
backup requests. Administrators can download verified files, play USB MP4
copies and add selected copies to the original video's lists. Local TS copies
are download-only in this tab. NFS deletion is not exposed. Source deletion
does not remove the NFS file. A missing mount never falls back to local disk.

Recording controls remain in live view's **REC** menu. Blink chooses its
configured destination (USB when Local Storage is active). **Close this live
view and keep saving** closes only the requesting viewer, without sending
`save=false`. Optional 15/30/60-second limits count received media time, not
loading or stalls, then close that viewer. Navigation/closing the application
can end it earlier. Other viewers are not disconnected and may extend the
shared clip. The provider records the whole session, including video before
REC: this is not an independently trimmed segment or a server-side timer.
Choose HA-local capture for a separate 15/30/60-second file. Provider
`save=false` still means discard saving, never stop-and-keep.

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
entries are adopted only on the same authenticated endpoint, by alias or by
their stored physical Ring ID. A generated discovery alias does not rename an
existing entry: a fresh status read must confirm that its original alias still
resolves to that physical ID. Entry/device/entity IDs, options and official
Ring bindings remain intact. Ambiguous matches or a changed physical ID abort
adoption; an unreachable original alias is not silently replaced. This avoids
another **Discovered → Add** prompt for an already configured intercom.
New intercoms are
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

Regression checks: `python -m pytest -q tests/test_release_*.py tests/test_ring_discovery_identity.py`. These tests
execute the integration's flow, identity migration, mount detection, and backup
code using isolated HA framework doubles and temporary files. They do not
contact vendors, mount shares, reconnect production accounts or open entrances.

## Vendor session and device health

When Ring revokes the Vistoda session (for example after a password change or
removing the device from Ring's authorized client devices), the Ring engine
answers HTTP 403 `reauth_required`. Vistoda starts the standard Home Assistant
re-authentication flow for that entry; the event listener pauses for five
minutes between checks and does not report a push outage. A bad bridge token
remains HTTP 401 and keeps its existing error.

`binary_sensor.*_intercom_connection` (Ring) follows the engine's `online`
status every minute and is unavailable when the bridge cannot be reached.
Each EZVIZ camera gets `binary_sensor.*_camera_connection`, read from the
Vistoda EZVIZ app's `/controls` (`online`, app 0.10+, standalone mode, the
default) or, when the camera is delegated to the official integration, from the
native Home Assistant EZVIZ integration (status 1 online, 2 offline). The
EZVIZ panel badge and **Connection** fact show the camera; **Vistoda app** shows
the bridge. Repairs raises `ezviz_core_unavailable` only while a delegated
EZVIZ entry has no loaded native integration; standalone entries never need
it. See [EZVIZ controls](ezviz-controls.md).

Ring engines from 0.15.0 report `push_degraded` and `last_missed_ding_at`.
Repairs shows `ring_push_silent_<entry_id>` while Ring stops delivering call
notifications and clears it when they resume. Each new missed call fires one
`vistoda_ring_missed_call` event with `entry_id`, `alias`, `device_name`,
`location_name`, `city` and `occurred_at` (epoch seconds), persisted so a
restart does not repeat it. Older engines omit these fields and nothing changes.
