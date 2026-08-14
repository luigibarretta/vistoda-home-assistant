# Home Assistant Media Bridge

Native Home Assistant Config Flow and entities for the provider-specific Rust
media bridges:

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

Add this repository as a HACS custom integration, install **Media Bridge**, then
restart Home Assistant once to load the Python component. Go to Settings →
Devices & services → Add integration → Media Bridge.

For EZVIZ, enter the private bridge URL, API token and configured camera alias.
The resulting camera uses the bridge's on-demand snapshot and MPEG-TS contract.

For Ring, enter the bridge connection first, then the Ring account and password
inside the native flow. If Ring sends an SMS, enter its six-digit code within
two minutes. An incorrect code consumes the challenge; start again instead of
retrying. Home Assistant never persists the account password, OTP or Ring token.

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
