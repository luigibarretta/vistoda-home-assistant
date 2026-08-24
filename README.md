# Vistoda for Home Assistant

Vistoda is the native Home Assistant control plane for private, provider-specific
Rust media bridges. The name joins *vista* and *custodia*: one guarded view over
the cameras and intercoms that remain inside the trusted network.

- Vistoda Blink connector: connects the standalone Rust Blink app and exposes
  its camera, control and media surface as native Home Assistant entities;
- Vistoda EZVIZ connector: fresh snapshot and shared MPEG-TS live camera;
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
device overview. Hidden, stable routes `/vistoda-ring`, `/vistoda-blink` and
`/vistoda-ezviz` provide focused controls without cluttering the sidebar. Their
panel assets use a release-versioned path, so the complete JavaScript module
graph updates coherently without requiring a browser cache reset.
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
paginated table exposes date, duration, size and confirmed deletion actions.
Each row can load its bounded media through the authenticated Home Assistant
WebSocket, play it with native browser controls and seek backward or forward by
ten seconds. The browser receives no bridge URL or bearer and revokes the local
media URL when playback changes or the panel closes.

Incoming-call notifications carry a unique call ID. Vistoda acknowledges that
ID only after the corresponding Ring audio session is active, allowing Home
Assistant to dismiss the tagged alert on every household Companion when the
first client answers.

The **Vistoda · RING** device owns the enhanced entity facade, **Audio Vistoda**,
a recording inventory sensor and a link to the provider-specific panel. The
official Ring device remains an optional rollback/event source. Vistoda adds
answering, full-duplex audio, battery, native controls and private recordings.
Microphone capture requires a browser gesture and cannot be modeled as a
background Home Assistant button safely.

The Blink view groups cameras into one navigable gallery and exposes arming,
motion, cached snapshots and native live opening. Snapshot refresh is explicit
so merely opening the panel does not wake battery cameras. The EZVIZ view opens
the protected HA camera and refreshes its snapshot; SceneTrove remains the
recording-ingest and spool owner.

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
