# Blink camera settings design QA

- Date: 2026-09-09
- Reference: official Blink Android **Device Settings** screenshot supplied by
  the user (`629 × 1280`).
- Implementation state: Vistoda Blink camera detail subpage, General section
  expanded, Italian locale and dark Home Assistant theme.
- Capture viewport: `390 × 794` CSS pixels at `1.61282` device scale, producing
  a `629 × 1280` image.
- Comparison artifact: `/tmp/vistoda-blink-comparison-1258x1280.png` (reference
  and implementation side by side).

## Result

The implementation follows the reference's category hierarchy while retaining
Home Assistant controls: General, Motion, Video and Photo, Audio and Privacy are
single-open accordion groups with a category icon, title and short description.
The dedicated camera subpage keeps those rows outside the camera page view.

The comparison exposed an author-style conflict with the HTML `hidden`
attribute: overview sections could remain visible above the detail subpage. A
shared `[hidden] { display:none !important; }` contract now makes the subpage
exclusive. The mobile capture has no horizontal overflow, clipped text,
overlapping controls or accidental pager content. Previous/next arrows retain
accessible names but have no hover tooltips.
