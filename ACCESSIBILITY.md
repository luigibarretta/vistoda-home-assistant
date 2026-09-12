# Vistoda accessibility statement

Last updated: 12 September 2026.

Vistoda aims to make its Home Assistant panel usable by as many people as possible. The current engineering target is [WCAG 2.2 Level AA](https://www.w3.org/TR/WCAG22/).

This is a voluntary project statement, not a certification. Vistoda does not yet claim formal WCAG conformance because an independent audit and complete assistive-technology test matrix have not been completed.

## Scope

This statement covers the Vistoda panel supplied by `vistoda-home-assistant`: Overview, Ring, Blink and EZVIZ views; camera pagination; settings; recording archives; lists; confirmation dialogs; and the information dialog.

Home Assistant itself, provider websites, provider media, browser permission prompts and third-party integrations are outside this statement’s direct scope.

## Measures implemented

- semantic buttons, links, form labels, headings, status regions and native dialogs;
- visible keyboard focus and keyboard-operable provider, camera, archive and zone controls;
- text labels or accessible names for icon controls, with state exposed through attributes such as `aria-current`, `aria-pressed`, `aria-checked`, `aria-expanded` and `aria-busy`;
- controls designed around a 44 by 44 CSS pixel touch target;
- layouts tested for reflow without page-level horizontal scrolling from 320 CSS pixels;
- color-independent text and icons for important states;
- animation and smooth scrolling disabled when reduced motion is requested;
- English and Italian accessible names and instructions.

## Internal audit evidence

The 12 September 2026 internal audit used synthetic Home Assistant data and Playwright. It covered Chromium, Firefox and WebKit; widths from 320 to 1280 CSS pixels; English and Italian; provider navigation; camera selection; archives; dialogs; error recovery; touch-target dimensions; and page overflow. It combines automated checks with human visual review, as recommended by the [W3C accessibility evaluation guidance](https://www.w3.org/WAI/test-evaluate/).

The audit also included visual review of mobile and desktop captures and keyboard checks for dialog opening, closing with Escape, focus return and Blink’s zone editor. Evidence is stored in the repository’s `artifacts/accessibility-audit-2026-09-12` directory during release review.

This document follows the structure recommended by the [W3C guidance for accessibility statements](https://www.w3.org/WAI/planning/statements/).

## Findings addressed in this audit

- Blink’s fixed zone canvas previously produced a one-pixel grid overflow in Firefox at one desktop width. Integer canvas dimensions now keep all 20 by 15 cells inside the image coordinate grid on every tested engine.
- The mobile zone editor now has a programmatic dialog name, traps focus while open, makes surrounding controls inert, closes with Escape and returns focus to its launcher.
- Blink’s zone-mode controls now use a labelled button group with `aria-pressed` state instead of an incomplete tab pattern.
- Privacy-zone delete controls increased from 32 to 44 CSS pixels.
- The hidden Ring intercom mirror selector was removed from the keyboard and accessibility trees; the visible labelled listbox remains the interactive selector.
- Small accent text and document links now use Home Assistant’s primary text color instead of depending on a theme accent color that could miss minimum contrast.

## Known limitations and verification gaps

- No complete NVDA, JAWS, VoiceOver or TalkBack regression pass has been completed.
- Camera video and provider recordings may not include captions, transcripts or audio descriptions.
- Blink’s 20 by 15 zone editor is keyboard operable, but editing hundreds of cells remains a complex task for some users.
- User-selected Home Assistant themes can change contrast outside the combinations covered by the release audit.
- Browser and operating-system microphone, autoplay and permission dialogs are controlled by those platforms.

## Feedback

Report an accessibility problem through the [Vistoda issue tracker](https://github.com/luigibarretta/vistoda-home-assistant/issues). Include the Vistoda version, Home Assistant version, browser, operating system, assistive technology, page and steps needed to reproduce the problem. Do not include credentials, camera images or private recordings.

For the Italian version, see [ACCESSIBILITY.it.md](ACCESSIBILITY.it.md).
