# Vistoda for Home Assistant

Vistoda is the native Home Assistant control plane for private, provider-specific
Rust media bridges. The name joins *vista* and *custodia*: one guarded view over
the cameras and intercoms that remain inside the trusted network.

- EZVIZ VTM Bridge: fresh snapshot and shared MPEG-TS live camera;
- Ring Intercom Bridge: secure password/SMS enrollment today, media entities
  only after the Rust bridge advertises verified capabilities.

## Security boundary

Home Assistant stores only the private bridge URL, its independent high-entropy
API token and a device alias. Ring password and SMS code pass once from the HA
backend to the bridge and are never saved in the config entry. The bridge owns
its rotating vendor session. There is no unlock action in this integration.

Keep bridge listeners private and firewall them to Home Assistant and approved
backend consumers. Do not add a public Traefik route.

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
