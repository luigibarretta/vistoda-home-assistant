# Vistoda for Home Assistant

Vistoda is the native Home Assistant control plane for private, provider-specific
Rust media bridges. The name joins *vista* and *custodia*: one guarded view over
the cameras and intercoms that remain inside the trusted network.

- Vistoda Blink connector: connects the standalone Rust Blink app and exposes
  its camera, control and media surface as native Home Assistant entities;
- Vistoda EZVIZ connector: manually refreshed cached snapshot and shared MPEG-TS live camera;
- Vistoda Ring connector: secure password/SMS enrollment, one listen-first
  full-duplex session, private local call recording and a native
  facade with native or delegated controls, battery, sensors and events;
- Vistoda Apple companion: authenticated iPhone/watchOS full-duplex audio over
  a bounded HA-to-bridge PCMU relay, without Ring or bridge secrets on-device.

## Security boundary

Home Assistant stores only the private bridge URL, its independent high-entropy
API token and a device alias. Ring password and SMS code pass once from the HA
backend to the bridge and are never saved in the config entry. The bridge owns
its rotating vendor session.

Vistoda reuses the bridge's single rotating Ring session for native battery,
last activity, volume and one-shot door controls. A global switch may delegate
controls to the official `ring` integration when its complete control surface is
detected. Native mode remains available without it. Ding and unlock events use
the official event source during the push-event migration. Door opening is
never retried automatically.

Keep bridge listeners private and firewall them to Home Assistant and approved
backend consumers. Do not add a public Traefik route.

The single **Vistoda** sidebar entry opens `/vistoda`, a unified health and
device overview. Focused views use `/vistoda/ring`, `/vistoda/blink` and
`/vistoda/ezviz`, so Home Assistant keeps the parent sidebar item selected.
Legacy `/vistoda-ring`, `/vistoda-blink` and `/vistoda-ezviz` links remain
registered and are rewritten to their canonical nested route. Panel assets use
a release-versioned path, so the complete JavaScript module graph updates
coherently without requiring a browser cache reset.
The browser inventory is authenticated, bounded and contains no bridge URL or
workload token.

The Ring view proxies signaling through Home Assistant's authenticated
WebSocket. **Avvia comunicazione** sends locally generated silence and never
opens a microphone. **Attiva microfono** requests permission only after its
button is pressed. Disabling it replaces the captured track with silence and
releases the microphone without ending inbound audio. The same page shows
battery and lets the user switch portone and volume controls between the native
Rust bridge and the official Ring integration. Opening requires an explicit
confirmation. The primary call action is contextual: it becomes **Termina**
only while a session exists, and the microphone control appears only then.

During an active panel call, **Registra questa chiamata** captures the remote
audio and includes the microphone only while it is enabled. The browser sends
the bounded WebM/MP4 through Home Assistant's authenticated WebSocket proxy;
it never receives a bridge token. **Registra automaticamente** is persisted
globally in the config entry and applies to every Vistoda browser. The archive
retains 30 days and at most 512 MiB; Ring Call Recording is not required. Its
paginated archive defaults to cards on mobile and to table rows on wider
screens; the user's explicit choice is kept in that browser. Both views expose
date, duration, size and confirmed deletion actions. A recording can belong to
multiple custom lists, which are stored centrally by Home Assistant and shared
across authenticated clients. A dedicated manager creates, renames and deletes
lists; deleting a list never deletes its underlying media. Each item can load its bounded media through
the authenticated Home Assistant WebSocket, play it with native browser
controls and seek backward or forward by ten seconds. The browser receives no
bridge URL or bearer and revokes the local media URL when playback changes or
the panel closes.

The archive header reports the effective storage directory. An Info action on
every row reveals and copies the exact file path without widening the mobile
table. Managed-app users choose private, app-config, media or share storage in
the Vistoda Ring app configuration; private remains the upgrade-safe default.

Incoming-call notifications carry a unique call ID. Vistoda acknowledges that
ID only after the corresponding Ring audio session is active, allowing Home
Assistant to dismiss the tagged alert on every household Companion when the
first client answers.

Core 2026.8.3 ships an affected Ring FCM dependency. Vistoda applies a bounded,
temporary startup guard for the public upstream padding/header-parser defects,
without logging push contents or modifying Home Assistant site packages.

The **Vistoda · RING** device owns the enhanced entity facade, **Audio Vistoda**,
a recording inventory sensor and a link to the provider-specific panel. When
several Ring config entries exist, the panel shows an intercom selector, keeps
the browser's last choice and honors an exact `entry` deep-link parameter. All
sessions, controls, recordings, lists and door actions remain scoped to that
config entry; `media_bridge.open_ring_door` requires `entry_id` only when the
choice would otherwise be ambiguous. The
official Ring device remains an optional rollback/event source. Vistoda adds
answering, full-duplex audio, battery, native controls and private recordings.
Microphone capture requires a browser gesture and cannot be modeled as a
background Home Assistant button safely.

The selected Ring device card owns its display identity: device name, Location
and city can be sourced independently from Ring, Home Assistant or a custom
value. Event history is intentionally read-only and uses that effective
identity for its rows and household unlock notifications.

The Blink view groups cameras into one navigable gallery and exposes arming,
motion, cached snapshots and native live opening. Snapshot
refresh is explicit so merely opening the panel does not wake battery cameras.
Every image shows its provider capture time; horizontal swipes and arrow
controls wrap continuously through the gallery, with round page indicators and
full-size touch targets. A model-aware detail view reads redacted settings from
the Blink provider. Administrators can change only typed, recognized fields;
each update carries a revision, is read back, and is restored when verification
fails. Verified v1 cameras also expose a touch editor for the native 20×15
activity grid and up to two privacy rectangles; Owl/Mini v2 zones remain hidden
when the provider rejects their schema. The Mini speaker control uses the
official integer scale 1–8. Unknown and unproven features stay hidden. Camera
settings follow the official app's five task-oriented sections, with one
accordion open at a time. On mobile, the header back button exits Vistoda to the
previous Home Assistant page, with the Casa dashboard as a safe fallback. The
EZVIZ view opens the protected HA camera and refreshes its snapshot only after
the explicit action. Landing reads the private cache without a provider request
and keeps the saved capture timestamp instead of replacing it with page-load time.

Blink and EZVIZ each have a standalone Vistoda live archive. A user selects 15,
30 or 60 seconds from the current shared stream; the provider writes a bounded
file and immutable SHA-256 manifest without generating a cloud motion event.
The per-camera UI consumes server-side ten-item pages and lists status,
timestamp, duration and size. Compact Material Design icon actions provide
playback, signed download, confirmed single or selected deletion and NFS backup.
The actual private add-on spool path is visible and copyable, always qualified
with the owning add-on because the same `/data/recordings` absolute path names
two isolated Supervisor-managed data namespaces. Blink and EZVIZ
recordings can belong to multiple centrally stored custom lists; users can
create, rename and delete lists without deleting media. Selecting several local
Blink/EZVIZ recordings—or several Blink USB clips—opens one multi-list picker;
the server adds every requested association atomically and preserves existing
memberships. EZVIZ remains
independent from SceneTrove: neither archive deletes or adopts the other's media.

Production mounts `/media/vistoda_archives` through the Home Assistant
Supervisor network-storage API. Vistoda refuses backup unless the path is an
actual NFS filesystem, at least 512 MiB remain, the file is at most 256 MiB and
its received byte count and SHA-256 match the provider manifest. Publication is
atomic and includes a JSON sidecar. The NAS child dataset has its own 20 GiB
hard quota, compression and an export restricted to iot-01; Vistoda never falls
back to the HAOS disk.

Blink Sync Module USB contents remain vendor-owned but are available through a
server-paginated inventory with signed playback/download and checksum-verified
NFS copy for one clip or the complete archive. The panel reports only the
provider-derived percentage of available space. Administrators may select and
delete one or more exact clips after confirmation. Compatible supports expose
formatting behind a destructive warning and an exact typed target phrase;
mount and eject remain absent. The current EZVIZ CP4 microSD contract remains
unavailable to the HAOS bridge. Blink WebRTC 4.1 signaling and
camera capability discovery are independently implemented, but media/session
negotiation is still gated; EZVIZ currently proves downstream H.264/AAC only.
Full-duplex buttons will appear only after real uplink and recovery canaries pass.

Native Apple clients use `/api/media_bridge/ring/audio/{entry_id}` with a Home
Assistant OAuth access token. HA resolves the private config entry and adds the
bridge bearer only server-side. The iPhone completes authorization-code login;
the Watch receives scoped connection state through WatchConnectivity, starts
muted and can listen and speak simultaneously. The existing HA actionable
notification remains the first delivery path until signed PushKit/APNs is
validated on physical Apple hardware.

## Installation

[![Install Vistoda through HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=luigibarretta&repository=vistoda-home-assistant&category=integration)

1. Install this repository as **Vistoda** through HACS.
2. Add the shared `vistoda-addons` repository to the Home Assistant app store.
3. Install and start **Vistoda Ring** and/or **Vistoda EZVIZ**.
4. Complete the automatically discovered integration under Settings → Devices
   & services.

The managed setup never asks for a bridge URL, port or workload token. Ring asks
for the account credentials and, when needed, the newest SMS code. EZVIZ asks
for account credentials and MFA; its app options contain only the camera serial
and a stable alias. Passwords and MFA codes are passed once to the private app
and are not persisted in the Home Assistant config entry.

Home Assistant Container/Core and SceneTrove deployments can keep the advanced
standalone path: run the provider image externally, then select manual backend
configuration and enter its private URL, workload token and alias.

The homelab production deployment remains SHA-pinned through
`deploy-ha-media-bridge.yml`. When a managed app announces the same provider
and alias as an existing external bridge, Vistoda adopts it in place: the
config-entry ID and entity identities stay stable while the private endpoint,
credential and unique ID move to the Supervisor app.

The internal Home Assistant domain remains `media_bridge`. This deliberately
stable identifier preserves existing config entries, entities and automations;
Vistoda is the user-facing product identity.

The provider repositories are `vistoda-blink`, `vistoda-ezviz` and
`vistoda-ring`. Their legacy executable, protocol and Home Assistant domain
names remain compatibility identifiers and are not separate products.

Remote bridges announce `_vistoda._tcp.local.` with provider and alias metadata.
Discovery pre-fills their private endpoint but never broadcasts the API token.
The loaded Blink Live Bridge initiates equivalent local-adapter discovery.

## Development

```bash
python -m ruff format --check .
python -m ruff check .
python -m pytest
python scripts/check_loc.py
node --test tests/*.mjs
```

Every maintained Python, JSON, Markdown, TOML and YAML file is limited to 250
physical lines. Tests reject generated caches and secret-shaped fixtures.

Architectural decisions are indexed in [`docs/adr/`](docs/adr/README.md).

Licensed under the MIT License.
