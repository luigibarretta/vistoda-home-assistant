# ADR 0025: Provider archive management and manual EZVIZ snapshots

- Status: accepted
- Date: 2026-09-10
- Supersedes the read-only Blink USB part of ADR 0024

## Context

Mobile archive rows became too wide once playback, download and backup were all
visible. Blink and EZVIZ recordings also lacked the custom-list organization
already available for Ring. The Blink Android 59.1 client proves exact Sync
Module clip-delete and compatible-media format routes. EZVIZ panel landing still
caused a snapshot request even though contacting a camera should be explicit.

## Decision

Provider archive rows use compact MDI icon actions with accessible names and
tooltips. Local Blink and EZVIZ recordings, plus Blink USB clips, share a Home
Assistant-private list model scoped by provider config entry. A recording may
belong to several lists. Creating, renaming or deleting a list never mutates
media. Successful deletion removes stale membership references.

The standalone providers return a bounded storage descriptor. Vistoda shows the
real internal add-on directory once with a copy action. It never presents the
path as a host or network mount. The UI also names the owning add-on: Blink and
EZVIZ may both report the absolute container path `/data/recordings`, but their
Supervisor-managed `/data` namespaces are physically isolated.

Blink USB inventory keeps backend pagination and matching frontend page
controls. Each clip has an explicit checkbox and guarded single or selected
deletion. The provider engine re-reads the current manifest and exact clip before
calling the native delete route. Formatting is admin-only, shown only when
`usb_format_compatible` is true, and requires typing `FORMATTA network/sync` in
a destructive modal. The panel shows only the provider-derived available-space
percentage. No eject or mount route is exposed.

EZVIZ snapshots are persisted as complete bounded JPEGs in private HA storage.
The camera entity serves only that cache. A provider fetch occurs solely through
the explicit authenticated refresh command; success updates the entity timestamp.
Loading that JPEG later never replaces its capture time with the page-load time.

## Consequences

- The dense mobile archive stays usable without hiding supported actions.
- Lists remain shared across authenticated HA clients and do not own media.
- Provider deletion is bounded to the exact current Blink manifest.
- Existing USB clips and the real format route are never destructive-test
  targets; tests are contract-only unless a disposable test-created clip/support
  is available.
- Direct recording to USB/microSD, EZVIZ microSD browsing and provider talk stay
  gated by separate transport and recovery evidence.
