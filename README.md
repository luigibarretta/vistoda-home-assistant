# Vistoda for Home Assistant

Vistoda is the native Home Assistant control plane for private, provider-specific
Rust media bridges. The name joins *vista* and *custodia*: one guarded view over
the cameras and intercoms that remain inside the trusted network.

- Blink local adapter: adopts the already authenticated Home Assistant relay
  and its existing live camera entities without a second login or duplicates;
- EZVIZ VTM Bridge: fresh snapshot and shared MPEG-TS live camera;
- Ring Intercom Bridge: secure password/SMS enrollment, one listen-first
  full-duplex session, private import of official call recordings and a native
  facade over the official Ring Intercom controls, sensors and events.

## Security boundary

Home Assistant stores only the private bridge URL, its independent high-entropy
API token and a device alias. Ring password and SMS code pass once from the HA
backend to the bridge and are never saved in the config entry. The bridge owns
its rotating vendor session.

Vistoda never opens a second Ring cloud control session. Its door button,
three volume controls, battery and last-activity sensors, ding event and unlock
event resolve the single official `ring` integration's Intercom device and
delegate to its entities. Resolution requires exactly one Ring Intercom source
for each capability and fails closed on missing or ambiguous sources. Door
opening is one-shot and is never retried automatically.

Keep bridge listeners private and firewall them to Home Assistant and approved
backend consumers. Do not add a public Traefik route.

The Vistoda · Ring sidebar panel proxies signaling through Home Assistant's
authenticated WebSocket. **Avvia comunicazione** sends locally generated
silence and never opens a microphone. **Attiva microfono** requests permission
only after its button is pressed. Disabling it replaces the captured track with
silence and releases the microphone without ending inbound audio.

The official Ring integration's ding event can call
`media_bridge.import_ring_recording`. Vistoda queues a bounded post-call import
from Ring's official Call Recording feature; it never opens a competing live
session. The private bridge stores only completed MP4 recordings for 30 days,
up to 512 MiB. Ring Call Recording must be enabled in the Ring app and may
require an eligible subscription; Ring plays its recording notice before the
conversation begins.

The **Vistoda · RING** device owns the enhanced entity facade, **Audio Vistoda**,
a recording inventory sensor and a link to the provider-specific panel. The
official Ring device remains the cloud source of truth; Vistoda adds answering,
full-duplex browser audio and the private recording workflow. Microphone capture
requires a browser gesture and cannot be modeled as a background Home Assistant
button safely.

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
```

Every maintained Python, JSON, Markdown, TOML and YAML file is limited to 250
physical lines. Tests reject generated caches and secret-shaped fixtures.

Architectural decisions are indexed in [`docs/adr/`](docs/adr/README.md).

Licensed under the MIT License.
