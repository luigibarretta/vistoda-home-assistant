# Vistoda for Home Assistant

Vistoda is one private Home Assistant interface for supported Ring Intercom,
Blink and EZVIZ devices. It combines device selection, live media, snapshots,
controls and local archives without exposing provider services or credentials to
the browser.

Blink recordings have a separate archive with **USB**, **Local HA** and **NFS
backup** tabs. REC stays in live view. See [recording limits and network backup
setup](docs/reconnect-and-network-backup.md): stopping your viewer preserves
provider saving but does not cut off other viewers or trim a shared USB clip.

The name joins *vista* and *custodia*: one guarded view of cameras and entrances
inside the trusted Home Assistant network.

Vistoda is an independent project and is not affiliated with or endorsed by the
device vendors it interoperates with. See the [full disclaimer](DISCLAIMER.md).

## What this repository owns

This repository provides the unified Vistoda panel and the Home Assistant
integration for Ring and EZVIZ. Blink also uses the small adapter from
[`vistoda-blink`](https://github.com/luigibarretta/vistoda-blink). Provider
sessions and protocols stay in separate Rust apps:

- [`vistoda-ring`](https://github.com/luigibarretta/vistoda-ring);
- [`vistoda-blink`](https://github.com/luigibarretta/vistoda-blink);
- [`vistoda-ezviz`](https://github.com/luigibarretta/vistoda-ezviz);
- [`vistoda-addons`](https://github.com/luigibarretta/vistoda-addons), the
  Home Assistant app catalog and canonical installation guide.

The internal Home Assistant domain remains `media_bridge` to preserve existing
config entries, entities and automations. Vistoda is the product name shown to
users.

## Supported scope

| Provider | Released functions | Boundary |
| --- | --- | --- |
| Ring | Multiple intercom selection, status, controls, event history, full-duplex browser audio and local call recordings; experimental native camera viewer | Experimental consumer APIs; Ring does not support this third-party use. Camera live remains hardware-unverified; see [camera scope](docs/RING_CAMERAS.md). Physical actions require an exact device binding; the Vistoda panel adds confirmation. |
| Blink | Multiple cameras, gesture-only snapshot paging, mobile fullscreen, Walnut live, hold-to-talk, supported settings/zones, versioned settings backups, provider-managed live saving, camera-filtered USB archives and NFS backup | Use Blink 0.19.0+ (0.18.0+ without USB eject/reconnect and status refresh). Blink routes a saved live to USB only when Local Storage is active; HA-local recording remains separate. Voice requires a supported offer, HTTPS and permission. Duplex is conditional on camera/browser AEC, not guaranteed by model. Validate sound and echo on your hardware. Cayuga remains disabled by provider policy. |
| EZVIZ | Multiple cameras, stored/manual snapshots, battery state, account arming, verified settings and PTZ through Vistoda's own EZVIZ login (standalone by default, app 0.10+), or delegated per camera to the official HA EZVIZ integration, compatible live streams, local recordings and NFS backup | Vistoda shows only settings the chosen source (the app, or `pyezvizapi` when delegated) reports with a readable current value. Writes require an administrator, explicit save confirmation, optimistic concurrency and read-after-write verification with rollback. Talk and direct microSD access are unavailable. Encrypted-stream compatibility is not universal. |
| Apple | Separate iPhone/watchOS project | Excluded from this release and its readiness claims. |

Vistoda is not a complete replacement for every vendor app. Keep the official
apps for account recovery and unsupported administration. Controls that a
provider or model cannot verify are hidden or disabled.

Home Assistant 2026.8.0 or newer is required. CI also tests 2026.9.1 with real
Home Assistant imports, config entries, coordinators, registries and config
flows on Python 3.14.

## Install on Home Assistant OS

[![Install Vistoda through HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=luigibarretta&repository=vistoda-home-assistant&category=integration)
[![Add the Vistoda app repository](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Fluigibarretta%2Fvistoda-addons)

1. Install **Vistoda** through HACS. Blink users also install **Vistoda Blink**.
2. Restart Home Assistant once.
3. Add the Vistoda Apps repository and install only the provider apps you use.
4. Complete each discovered flow under **Settings → Devices & services**.

The normal managed setup does not ask for a bridge URL, port or workload token.
Provider credentials and MFA values are sent only to the private provider app
during enrollment. EZVIZ additionally needs each camera serial in its app
options before startup.

Ring discovery recognizes an existing physical intercom even when the app
advertises a generated alias. It preserves the configured alias and HA entities
after verifying the original route; it does not require another account login.
See [discovery and reconnect safeguards](docs/reconnect-and-network-backup.md).

Follow the complete [English setup guide](https://github.com/luigibarretta/vistoda-addons/blob/main/GETTING_STARTED.md)
or [guida italiana](https://github.com/luigibarretta/vistoda-addons/blob/main/GETTING_STARTED.it.md).
The exact tested versions are listed in the
[compatibility matrix](https://github.com/luigibarretta/vistoda-addons/blob/main/COMPATIBILITY.md).

## What to expect

The single **Vistoda** sidebar item opens `/vistoda`. Provider views use
`/vistoda/ring`, `/vistoda/blink` and `/vistoda/ezviz`, so the parent sidebar
entry stays selected. Old top-level provider URLs are redirected to these
canonical routes.

Ring presents every enrolled intercom as an explicitly selected device. History,
identity, controls, notifications, audio and recordings remain tied to that
physical entrance. Opening is never retried automatically.
Vistoda can replace the vendor apps for day-to-day alerts: a revoked Ring
session opens Home Assistant's standard re-authentication flow, the
`Intercom connection` and per-camera EZVIZ `Camera connection` sensors report
the device itself (the EZVIZ panel shows the Vistoda app link separately), and
Repairs warns when Ring stops delivering call notifications or when an EZVIZ
camera delegated to the official EZVIZ integration finds it not loaded
(standalone cameras, the default, never need it). Automations can
listen for `vistoda_ring_missed_call`; see
[Reconnect accounts](docs/reconnect-and-network-backup.md#vendor-session-and-device-health).

Blink and EZVIZ present multiple cameras in stable, circular page views. Opening
a page uses the latest stored snapshot; a new capture happens only after an
explicit action. Provider settings and actions reflect reported capabilities.

For fullscreen and microphone availability, see [Blink live controls](docs/blink-live-controls.md).

Blink and EZVIZ keep local recording controls in a closed accordion. Recording
archives share a 10/25/50/100 page-size selector; Blink/EZVIZ request that page
size from the backend, while Ring pages its local archive metadata in the UI.
On narrow touch screens a long press enters selection mode; dragging across
cards extends the selection, while the always-visible counter and selection
button provide an explicit keyboard and screen-reader alternative.
System cards share one Arm/Disarm button, updated only after the state is
confirmed, with a success toast. Like Ring, each EZVIZ camera explicitly chooses
its control source: standalone (the default) uses the Vistoda EZVIZ app 0.10+
and its account alarm panel, while the per-camera switch **Delegate controls to
the official EZVIZ integration** uses the native integration, matched by camera
identity, and its own alarm panel. Vistoda never silently falls back between the
two; see [EZVIZ controls](docs/ezviz-controls.md). The
camera name comes from the native integration when present. An HA area is
explicitly labeled as such, not presented as the room name from the vendor app.

In **Blink → Camera detail → General settings**, supported battery cameras expose
their native temperature alert switch and cold/hot thresholds. Temperatures use
Home Assistant's °C/°F preference. Edit the values, then select **Save changes**;
nothing is sent while adjusting a control. If Blink has never saved thresholds,
the fields are empty: enter both to initialize them explicitly. Initial setup
must be saved separately from unrelated camera settings. Blink requires a gap of
at least 10 °F (about 5.6 °C); its integer-Fahrenheit storage can round °C values.
Vistoda preserves the current calibration and verifies saved values by reading
them back. A failed first initialization cannot restore an absent threshold;
reload and inspect the reported state before retrying.

These switches configure **native Blink push notifications**. Vistoda Blink also
publishes one `Temperatura fuori soglia` binary sensor per supported camera, so
operators can build a separate Home Assistant Companion notification without
reimplementing Fahrenheit threshold comparison. Cameras without the temperature
capability (including the original Mini) do not expose the controls or that
state as available; missing telemetry disables writes rather than guessing a
value.

The Blink system card can retain up to 25 named, all-camera settings backups.
Restore matches each camera by provider serial or stable camera ID, creates a
rollback snapshot, preflights every field and uses revision checks. A concurrent
change or a non-reversible uninitialized temperature threshold stops the restore
instead of overwriting or reporting partial values as successful. Single-camera
backup/restore is supported by the backend contract but is intentionally not in
the panel yet.

Ring, Blink and EZVIZ use separate app-owned archives. The same displayed
`/data/recordings` path in two apps does not mean the same directory: each Home
Assistant app has an isolated data volume. Vistoda shows the owning provider and
effective path. Supported archives are paginated server-side and allow playback,
download, confirmed deletion, list membership and verified network backup.
The Blink Sync Module section reports connection, firmware and USB storage used,
and follows the official app's USB states: **Format USB Drive**, **USB Drive
Disconnected** (reconnect), **Insert USB Drive**, **USB Drive Full** (safe
eject) and **USB Drive Not Compatible**, with the same help links, the
almost-full and backup-in-progress banners, the last backup failure reason and
a 30-second status refresh while the section is visible. Safe eject and
reconnect need Blink 0.19.0+ and an administrator; formatting still requires
the typed confirmation. Wi-Fi migration and Sync Module removal remain visible
but disabled until their complete recovery paths are independently verified.

For NFS or SMB backup, add the storage in **Settings → System → Storage** with
usage **Media**, then select its storage name in the Vistoda integration options.
Vistoda requires a real writable network mount with at least 512 MiB free and
never falls back silently to the Home Assistant disk. An administrator can turn
on the hourly, incremental backup from the **NFS backup** tab or the Blink
options: each pass copies and verifies Blink USB clips and ready **Local HA**
recordings (up to 20 new files per pass, no deletion propagation). In Blink,
start recordings from the live **REC** menu; the local archive remains available
for playback and file management. Provider saving covers the shared live
session, while HA-local capture offers 15/30/60 seconds. With a Blink adapter
that supports it, the **Local HA** tab also shows **Motion recording**: choose
cameras and a 15/30/60-second length, and motion clips get a **Motion** badge.
Recording starts after Blink reports the motion (about 30–60 seconds), so it
captures the following scene, and it wakes battery cameras. See the
[network-backup guide](docs/reconnect-and-network-backup.md).

## Security model

Provider apps keep credentials, rotating sessions and workload tokens in their
private persistent storage. The browser authenticates to Home Assistant and
never receives a provider token or private bridge URL. Provider ports have no
host mapping by default and must not be published through a public reverse
proxy.

The Vistoda panel confirms door actions, media deletion and storage formatting.
Authorized Home Assistant buttons or automations can call door actions without
that panel modal. Requests remain device-scoped and fail when identity or
capability is ambiguous. See [SECURITY.md](SECURITY.md) and the
[architecture decisions](docs/adr/README.md).

## Advanced deployments

Home Assistant Container/Core and SceneTrove users may run provider containers
on a private network and configure their URL, workload token and alias manually.
This path assumes the operator owns container security, persistent storage,
updates and firewall policy; it is not the default onboarding route.

Remote bridges may announce `_vistoda._tcp.local.` with provider and alias
metadata. Discovery never broadcasts an API token.

## Development

Start with [CONTRIBUTING.md](CONTRIBUTING.md) for the repository map, toolchains,
validation commands and cross-repository release order.

The local checks for this repository are:

```bash
python -m pip install -e '.[dev]'
python -m ruff format --check .
python -m ruff check .
python -m pytest
python scripts/check_loc.py
node --test tests/*.mjs
```

Tests use synthetic provider boundaries and do not actuate devices. Tag releases
require the same commit's complete CI validation; a local pass is not a release
gate.

## Further documentation

- [Reconnect accounts and configure network backups](docs/reconnect-and-network-backup.md)
  ([Italiano](docs/reconnect-and-network-backup.it.md));
- [Frontend release hardening](docs/frontend-release-hardening.md)
  ([Italiano](docs/frontend-release-hardening.it.md));
- [Accessibility statement](ACCESSIBILITY.md)
  ([Italiano](ACCESSIBILITY.it.md));
- [Independent-project disclaimer](DISCLAIMER.md)
  ([Italiano](DISCLAIMER.it.md));
- [Architecture decisions](docs/adr/README.md);
- [Archived mobile QA evidence](design-qa.md).

## Author and support

Created and maintained by [Luigi Barretta](https://github.com/luigibarretta).
If Vistoda is useful to you, you can [support its development on Ko-fi](https://ko-fi.com/luigibarretta).

Licensed under the MIT License.
