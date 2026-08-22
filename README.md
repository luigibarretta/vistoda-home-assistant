# Vistoda for Home Assistant

Vistoda is the native Home Assistant control plane for private, provider-specific
Rust media bridges. The name joins *vista* and *custodia*: one guarded view over
the cameras and intercoms that remain inside the trusted network.

- Blink local adapter: adopts the already authenticated Home Assistant relay
  and its existing live camera entities without a second login or duplicates;
- EZVIZ VTM Bridge: fresh snapshot and shared MPEG-TS live camera;
- Ring Intercom Bridge: secure password/SMS enrollment, one listen-first
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

The Vistoda · Ring sidebar panel proxies signaling through Home Assistant's
authenticated WebSocket. **Avvia comunicazione** sends locally generated
silence and never opens a microphone. **Attiva microfono** requests permission
only after its button is pressed. Disabling it replaces the captured track with
silence and releases the microphone without ending inbound audio. The same page
shows battery and lets the user switch portone and volume controls between the
native Rust bridge and the official Ring integration. Opening requires an
explicit confirmation.

During an active panel call, **Registra questa chiamata** captures the remote
audio and includes the microphone only while it is enabled. The browser sends
the bounded WebM/MP4 through Home Assistant's authenticated WebSocket proxy;
it never receives a bridge token. **Registra automaticamente** is persisted
globally in the config entry and applies to every Vistoda browser. The archive
retains 30 days and at most 512 MiB; Ring Call Recording is not required.

The **Vistoda · RING** device owns the enhanced entity facade, **Audio Vistoda**,
a recording inventory sensor and a link to the provider-specific panel. The
official Ring device remains an optional rollback/event source. Vistoda adds
answering, full-duplex audio, battery, native controls and private recordings.
Microphone capture requires a browser gesture and cannot be modeled as a
background Home Assistant button safely.

Native Apple clients use `/api/media_bridge/ring/audio/{entry_id}` with a Home
Assistant OAuth access token. HA resolves the private config entry and adds the
bridge bearer only server-side. The iPhone completes authorization-code login;
the Watch receives scoped connection state through WatchConnectivity, starts
muted and can listen and speak simultaneously. The existing HA actionable
notification remains the first delivery path until signed PushKit/APNs is
validated on physical Apple hardware.

## Installation

The production deployment is SHA-pinned and managed by the private Ansible
playbook `deploy-ha-media-bridge.yml`. After the play loads the component, go
to Settings → Devices & services → Add integration → Vistoda.

The repository keeps the standard HACS integration layout and metadata for a
possible future public release. HACS cannot install a private GitHub repository,
so do not present the current private mirror as a HACS custom repository.

For EZVIZ, enter the private bridge URL, its dedicated API token and the camera
alias already configured in the bridge. Enroll the EZVIZ account and device
verification code in the Rust bridge first; they do not belong in Vistoda. The
resulting camera uses the bridge's on-demand snapshot and MPEG-TS contract.

For Ring, enter the bridge connection first, then the Ring account and password
inside the native flow. If Ring sends an SMS, enter its six-digit code within
two minutes. An incorrect code consumes the challenge; start again instead of
retrying. Home Assistant never persists the account password, OTP or Ring token.

The internal Home Assistant domain remains `media_bridge`. This deliberately
stable identifier preserves existing config entries, entities and automations;
Vistoda is the user-facing product identity.

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
