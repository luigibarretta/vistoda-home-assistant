# Vistoda mobile design QA

final result: passed

- Date: 2026-09-10
- Current implementation: deployed Vistoda Home Assistant `0.24.2`.
- Blink evidence browser: Google Chrome, mobile viewport `390 × 794` CSS pixels.
- Deployed capture:
  `/home/ansible/audits/vistoda-0.22.1/blink-mobile.png` (`390 × 2720`).

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

The `0.22.1` browser transport waits for ICE gathering and embeds the gathered
candidates in the Blink offer before subscribing. Its canary records only a
sanitized structural summary (media sections, directions, codecs and candidate
types), never SDP addresses, ICE credentials or device identifiers.

## Blink USB and local archives

The USB summary presents `USB: active`, `Spazio disponibile` and `Ultimo backup`
on a vertically centered fact row. Server-side ten-item pages remain legible at
mobile width. Row actions use compact icon buttons with accessible labels for
playback, download, NFS backup, list membership and deletion; destructive
actions remain visually distinct and require confirmation.

The capture shows no horizontal overflow, clipped labels, overlapping controls
or undersized action targets. Local archive paths are visible with their owning
add-on namespace, and the cards/table selector communicates its active state.

## Ring event history

- Implementation: deployed Vistoda Home Assistant `0.24.2` and Vistoda Ring
  app `0.12.0`, served by Home Assistant from `/vistoda_static/0.24.2`.
- Browser: Google Chrome, `393 × 800` CSS pixels at device scale `1.6`, producing
  the same `629 × 1280` raster dimensions as the supplied Ring reference.
- Reference: `artifacts/qa/ring-reference.jpg`.
- Deployed capture: `artifacts/qa/ring-history-mobile.png`.
- Side-by-side comparison: `artifacts/qa/ring-history-comparison.png`.

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
final pass has all three 44 px header controls visible, no document-level
horizontal overflow, a deliberately scrollable localized filter row and zero
console errors. Ring's combined `Home in Casoria` Location label is displayed
once; notification wording separately avoids repeating the structured city.
