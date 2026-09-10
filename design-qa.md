# Vistoda mobile design QA

final result: passed

- Date: 2026-09-10
- Implementation: deployed Vistoda Home Assistant `0.22.1`, served directly by
  Home Assistant from `/vistoda_static/0.22.1`.
- Browser: Google Chrome, mobile viewport `390 × 794` CSS pixels.
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
