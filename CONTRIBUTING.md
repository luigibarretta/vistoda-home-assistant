# Contributing to Vistoda

Vistoda is a family of small repositories with explicit ownership boundaries.
Choose the repository that owns the behavior before changing code. Do not copy
provider credentials, tokens, serials, recordings or packet captures into a
checkout, issue or test fixture.

For a Home Assistant installation, use the [operator guide](https://github.com/luigibarretta/vistoda-addons/blob/main/GETTING_STARTED.md).
This document is for source development.

## Repository map

| Repository | Owns | Does not own |
| --- | --- | --- |
| [`vistoda-home-assistant`](https://github.com/luigibarretta/vistoda-home-assistant) | Unified panel, Ring/EZVIZ HA adapters, authenticated browser proxy, lists and network backup | Vendor sessions and provider protocols |
| [`vistoda-blink`](https://github.com/luigibarretta/vistoda-blink) | Blink Rust provider app and Blink HA adapter | Ring, EZVIZ or public ingress |
| [`vistoda-ring`](https://github.com/luigibarretta/vistoda-ring) | Ring enrollment, intercom identity, controls, events and audio transport | Browser UI and HA entity registry |
| [`vistoda-ezviz`](https://github.com/luigibarretta/vistoda-ezviz) | EZVIZ enrollment, camera binding, snapshots and media transport | SceneTrove retention or HA frontend state |
| [`vistoda-addons`](https://github.com/luigibarretta/vistoda-addons) | HAOS app catalog, app options, user installation and release compatibility | Provider implementation |
| [`lib-vistoda-provider-kit`](https://git.luigibarretta.com/luigibarretta/lib-vistoda-provider-kit) | Shared Supervisor bootstrap and discovery helpers | Provider configuration or runtime framework behavior |

Stable compatibility identifiers such as the `media_bridge` and
`blink_live_bridge` Home Assistant domains must not be renamed as part of a
product-label cleanup.

## Toolchains

- Python 3.13 or newer for both Home Assistant integrations;
- Rust 1.88 for Blink and EZVIZ;
- Rust 1.96 for Ring;
- Node.js for the Vistoda browser tests;
- Docker or Podman for provider image checks.

Use the committed lockfiles. Tests use synthetic fixtures and should not require
a vendor account or network connection.

## Validate a change

### Vistoda Home Assistant

```bash
python -m pip install -e '.[dev]'
python -m ruff format --check .
python -m ruff check .
python -m pytest
python scripts/check_loc.py
node --test tests/*.mjs
npm install --no-save --package-lock=false playwright@1.61.1
npx playwright install chromium firefox webkit
for engine in chromium firefox webkit; do
  NODE_PATH="$PWD/node_modules" BROWSER_ENGINE="$engine" node tests/browser/panel-responsive.mjs
done
```

### Vistoda Blink

```bash
python -m pip install '.[dev]'
python -m ruff format --check .
python -m ruff check .
python -m pytest
python scripts/check_loc.py
cargo fmt --manifest-path addon/vistoda_blink_engine/Cargo.toml --check
cargo clippy --manifest-path addon/vistoda_blink_engine/Cargo.toml --all-targets --all-features -- -D warnings
cargo test --manifest-path addon/vistoda_blink_engine/Cargo.toml
```

### Vistoda Ring

```bash
cargo fmt --all -- --check
cargo clippy --locked --all-targets --all-features -- -D warnings
cargo test --locked --all-targets
cargo audit --deny warnings
docker build -t ring-intercom-bridge:test .
```

### Vistoda EZVIZ

```bash
cargo fmt --all -- --check
cargo clippy --locked --all-targets --all-features -- -D warnings
cargo test --locked --all-targets
cargo audit --deny warnings
docker build -t ezviz-vtm-bridge:test .
```

### App catalog and provider kit

```bash
# vistoda-addons
python scripts/check.py
python -m unittest discover -s tests -p 'test_*.py'

# lib-vistoda-provider-kit
sh -n dist/vistoda-app-bootstrap.sh tests/bootstrap-test.sh
tests/bootstrap-test.sh
```

Run each command from the repository named by the heading. CI remains the
release authority; a local pass is not a substitute for tag validation.

## Provider canaries

Real-device canaries are opt-in release evidence, not unit tests. Run them only
against devices you own, with a deliberate action scope and a cleanup plan.

- Prefer a powered camera for media tests.
- Do not wake battery cameras during routine validation.
- Stop after provider throttling, account warnings, HTTP 401/403/429 or an
  unexpected physical action.
- Never use door opening, file deletion or storage formatting as a generic
  smoke test.
- Store sanitized evidence outside the repository; do not publish media or
  device identifiers.

## Cross-repository changes

When an API contract changes:

1. update the provider OpenAPI contract and implementation;
2. update its HA adapter or the main Vistoda integration;
3. add deterministic producer and consumer tests;
4. update the app metadata and compatibility matrix;
5. release the provider image and app before the consuming integration.

The provider app must remain private. Browser clients use Home Assistant's
authenticated proxy and must never receive a provider workload token.

## Documentation standard

Lead with the user outcome, prerequisites and the shortest verified path. Put
protocol detail in ADRs or research notes. Clearly label historical evidence;
do not call an old deployment “current”. Examples must contain synthetic IDs and
copyable placeholders with an instruction explaining how to replace them.

Update the [tested release set](https://github.com/luigibarretta/vistoda-addons/blob/main/COMPATIBILITY.md)
whenever a coordinated release changes one of its versions.
