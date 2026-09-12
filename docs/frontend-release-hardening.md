# Frontend release checks

The panel uses a shrinking host/container layout and a two-column navigation
grid below 600 px. Shared controls have a minimum 44 × 44 px hit area. Blink's
camera indicators retain their 8 px circles inside 44 px buttons; the indicator
group wraps when necessary. All Vistoda roots must include `BASE_STYLES`.

Inventory loading failures show a connection error with the existing Refresh
action. Provider setup is offered only after inventory succeeds. The back
button uses Home Assistant's default dashboard when available and `/lovelace`
otherwise; it contains no installation-specific dashboard path.

Ring selection shows both device and location names. The unlock confirmation
names the selected entrance. History is configured with that exact entry,
clears previous events immediately, and ignores stale asynchronous responses.
EZVIZ selection routes snapshot refresh and archive access by camera alias.
An unambiguous one-camera/one-entry installation remains compatible; multiple
cameras without an exact alias match cannot refresh another camera's image.
Merely opening the page continues to read saved snapshots only.

## Localization

`panel-localize.js` provides English and Italian catalogs, Home Assistant
language selection, English fallback, named interpolation, and explicit
`data-i18n`, `data-i18n-title`, and `data-i18n-aria-label` markers. The catalog
tests require key and interpolation parity. Messages are assigned through
`textContent`, never interpreted as HTML. Device names and user-provided values
must not be automatically translated.

The shell, overview, loading/error/setup states, provider introductions,
snapshot timestamps and Ring history use this catalog. `panel-copy.js` and its
scoped common/Ring/Blink/storage catalogs cover advanced camera settings,
archives, lists, recording/audio statuses, confirmations, dialogs, accessible
names and tooltips. Source-owned labels use `copy(context, source, parameters)`
or explicit `data-copy` / `data-copy-<attribute>` markers. Catalog lookup never
runs on arbitrary rendered text, device names, paths, list names, input values
or vendor messages. Unknown languages fall back to English; missing authored
copy falls back to its source instead of breaking device controls. Tests enforce
catalog coverage and parameter parity. Avoid interpreting translated strings
or user interpolation as HTML.

The native 20 × 15 Blink zone grid sits in a bounded scroll region, keeping
every cell at least 44 px without clipping its coordinate map to the image.
Tab and Space toggle activity cells without a device write; Save remains an
explicit, confirmed operation. Privacy and read-only cells cannot be toggled.

## Automated verification

Blink compatible live must also work on a cold direct `/vistoda/blink` entry,
before any Lovelace dashboard has been visited. `ha-card-helpers.js` loads the
Lovelace module through Home Assistant's registered route loader when the
global card helper is absent. It does not change the URL, mount another
dashboard, guess asset hashes or request camera media during bootstrap.
Closing live during loading prevents subsequent card creation.
`tests/browser/ha-card-helpers.mjs` exercises this DOM path in all three browser
engines with a synthetic loader; actual HA/media verification remains separate.

```sh
node --test tests/*.mjs
NODE_PATH=/path/to/node_modules node tests/browser/panel-responsive.mjs
```

The browser script requires Playwright and its Chromium installation. It serves
the current checked-out modules from a loopback-only HTTP server and supplies a
synthetic Home Assistant object. It checks overview, Ring, Blink, EZVIZ and Ring
history in English and Italian at 320, 360, 393, 600, 768 and 1280 px: document overflow, visible
button/link/select/range dimensions, active navigation, 8 px Blink indicators,
two same-named Ring entrances, history identity, inventory failure and recovery,
and uncaught browser errors. It also opens Ring identity (including focus return),
recording info and list dialogs, USB format confirmation, Blink settings/quality
and zone editing. User values deliberately matching Italian UI copy remain
unchanged. Zone grid dimensions and keyboard editing are checked. Its service-call implementation always throws;
only an allowlisted synthetic read contract is accepted.

This is a deterministic frontend gate, not proof of a deployed Home Assistant
runtime, vendor connectivity, screen-reader output or actual device actions.
