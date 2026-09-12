# Vistoda for Home Assistant

Vistoda is one private Home Assistant interface for supported Ring Intercom,
Blink and EZVIZ devices. It combines device selection, live media, snapshots,
controls and local archives without exposing provider services or credentials to
the browser.

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
| Ring | Multiple intercom selection, status, controls, event history, full-duplex browser audio and local call recordings | Experimental consumer APIs; Ring does not support this third-party use. Physical actions require an exact device binding; the Vistoda panel adds confirmation. |
| Blink | Multiple cameras, stored/manual snapshots, Walnut live, supported settings and zones, cloud/USB/local archives and NFS backup | Cayuga/WebRTC microphone and full-duplex talk are disabled by current provider policy. Settings vary by model. |
| EZVIZ | Multiple cameras, stored/manual snapshots, compatible live streams, local recordings and NFS backup | Talk and direct microSD access are unavailable. Encrypted-stream compatibility is not universal. |
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

Blink and EZVIZ present multiple cameras in stable, circular page views. Opening
a page uses the latest stored snapshot; a new capture happens only after an
explicit action. Provider settings and actions reflect reported capabilities.

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

These switches configure **native Blink push notifications**, not Home Assistant
Companion notifications. The Blink app needs notification permission. Cameras
without the temperature capability (including the original Mini) do not expose
the controls; missing telemetry disables writes rather than guessing a value.

Ring, Blink and EZVIZ use separate app-owned archives. The same displayed
`/data/recordings` path in two apps does not mean the same directory: each Home
Assistant app has an isolated data volume. Vistoda shows the owning provider and
effective path. Supported archives are paginated server-side and allow playback,
download, confirmed deletion, list membership and verified network backup.

For NFS or SMB backup, add the storage in **Settings → System → Storage** with
usage **Media**, then select its storage name in the Vistoda integration options.
Vistoda requires a real writable network mount with at least 512 MiB free and
never falls back silently to the Home Assistant disk. See the
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
