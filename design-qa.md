# Archived Vistoda mobile design QA

Result at capture: passed.

This is historical evidence from 2026-09-10, not the current release status.
It covers Vistoda Home Assistant `0.24.5`, Vistoda Ring `0.12.0` and an earlier
Blink browser transport. Current release gates are documented in
[`docs/frontend-release-hardening.md`](docs/frontend-release-hardening.md).

The Blink capture used Google Chrome at a `390 × 794` CSS-pixel viewport. Visual
artifacts were retained in the private QA archive and are not distributed in
this source repository.

## Navigation and camera gallery

The deployed mobile browser canary proves a visible `44 px` back control and
returns from the Blink provider route to the previous Home Assistant page. The
canonical route remains `/vistoda/blink`, so the Vistoda sidebar item stays
active on every provider subpage.

Blink snapshot paging wraps in both directions by arrow or horizontal swipe.
Indicators render as `8 × 8 px` circles with a `50%` radius inside `28 px`
touch targets. Each camera exposes its provider capture timestamp; the canary
also verifies that every camera remains available when the gallery is changed.

## Camera controls and settings

The live, snapshot and motion controls combine state-aware Material Design
icons with labels. Battery, temperature and recent clips use the same icon and
label hierarchy. General, Motion, Video and Photo, Audio and Privacy are grouped
as single-open accordions on a dedicated camera-detail page, following the
official Blink information architecture without forcing long settings forms
into the gallery.

Current provider values are read before controls are rendered. The deployed
canary confirms early notification is active, image flip is inactive and all
three requested video-quality descriptions are present. The activity/privacy
zone editor preserves the native `20 × 15` model at a measured `1.7777` aspect
ratio.

The `0.22.1` browser transport captured here waited for ICE gathering and embedded the gathered
candidates in the Blink offer before subscribing. Its canary records only a
sanitized structural summary (media sections, directions, codecs and candidate
types), never SDP addresses, ICE credentials or device identifiers.

## Blink USB and local archives

The archived capture presented `USB: active`, `Spazio disponibile` and `Ultimo backup`.
The current panel uses compact icon/value facts and a storage-used gauge; their
full labels appear on hover or focus. Server-side pages remain legible at
mobile width. Row actions use compact icon buttons with accessible labels for
playback, download, NFS backup, list membership and deletion; destructive
actions remain visually distinct and require confirmation.

Current mobile archives use a custom 10/25/50/100 page-size control, an
always-visible total/selection count and long-press plus drag selection without
reserving an empty checkbox column. The explicit selection button remains the
accessible alternative.

The capture shows no horizontal overflow, clipped labels, overlapping controls
or undersized action targets. Local archive paths are visible with their owning
add-on namespace, and the cards/table selector communicates its active state.

## Ring event history

- Captured implementation: Vistoda Home Assistant `0.24.5` and Vistoda Ring
  app `0.12.0`, served by Home Assistant from `/vistoda_static/0.24.5`.
- Browser: Google Chrome, `393 × 800` CSS pixels at device scale `1.6`, producing
  the same `629 × 1280` raster dimensions as the supplied Ring reference.
- Reference and comparison images were retained in the private QA archive.

The deployed capture uses real Ring history and Home Assistant's real Material
Design icon component. It preserves the supplied hierarchy: compact header,
access/device/event filters, day grouping, event icon, title, device name and
right-aligned time. The layout retains Vistoda's existing card language rather
than copying the Ring app chrome.

The first page contained 20 real events. The browser canary loaded the next
server page, exercised the event filter, refreshed the first page and verified
the back action. It also opened and cancelled the identity dialog, confirming
Ring, Home Assistant and custom sources without changing the saved values.

The first visual pass exposed the mobile header's minimum-content overflow. The
final pass has all three 44 px header controls visible, every event glyph
centered in its circular background, no document-level horizontal overflow, a
deliberately scrollable localized filter row and zero console errors. Ring's
combined `Home in Casoria` Location label is displayed once; notification
wording separately avoids repeating the structured city.

## EZVIZ settings and swipe regression check (0.32.0)

- Reference: owner-provided EZVIZ Settings screenshots at 629 × 1280.
- Capture: `/home/ansible/audits/vistoda-0.32.0-local/mobile.png`, 390 px mobile viewport.
- Blink gesture listeners are confined to the image stage and only the snapshot
  receives drag transforms; the camera card no longer moves.
- EZVIZ shows the bound battery value (`55%` in the fixture) and nine compact,
  icon-led settings groups. Actionable native HA entities open their standard
  control dialog; unsupported groups state that the provider does not expose a
  control.
- The details page has no horizontal overflow, keeps 44 px primary targets and
  preserves the existing provider typography, spacing and theme.

final result: passed

## EZVIZ provider controls and stationary snapshot (0.32.1)

- References: owner-provided EZVIZ Battery, Intelligent Detection, Message
  Notification, Audio, Image, Privacy and Network Settings screenshots.
- Capture: `/home/ansible/audits/vistoda-0.32.1-local/mobile.png`, 390 px mobile viewport.
- The snapshot remains centered and stationary throughout the swipe gesture. The
  gesture still changes camera, but no partial card, cloned image or settling
  transform is shown.
- Nine icon-led settings accordions remain within the mobile viewport. Verified
  provider controls are merged with native Home Assistant entities in their
  corresponding category; unavailable or ambiguous private controls are not
  presented as writable.
- Provider changes are staged, expose one sticky Save action, require an explicit
  confirmation dialog and retain 44 px or larger interactive targets.
- The browser fixture exposed three provider-backed rows and reported an empty
  snapshot transform during an active pointer drag. No horizontal overflow or
  visual displacement was observed.

final result: passed
