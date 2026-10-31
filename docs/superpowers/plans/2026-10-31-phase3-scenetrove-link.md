# Phase 3: the SceneTrove link — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** From a Vistoda EZVIZ event, open SceneTrove on the right device at the
event instant; Vistoda presents SceneTrove and lets the user set its address.

**Architecture:** SceneTrove gains a URL contract `?device=<folder>&at=<ISO
instant>` handled once at load (select device, day, covering clip, seek). The
Vistoda integration stores `scenetrove_url`/`scenetrove_device` per EZVIZ entry,
publishes them in the panel metadata, shows an info card when unset, and puts
"Apri in SceneTrove" first in the event modal.

**Tech Stack:** SceneTrove Svelte 5 UI (node unit tests, `npm run test:unit`),
Vistoda HA integration (Python, vanilla JS, pytest, node:test).

**Spec:** `docs/superpowers/specs/2026-10-29-event-archive-and-scenetrove-link-design-part2.md` section 4.

## Global Constraints

- SceneTrove repo: no vendor names anywhere (brand gate bans `ezviz`); run `node third_party/repo-tooling/ci-local.mjs --quick` before pushing; heavy builds through the build lock.
- Link format, exact: `<scenetrove_url>/?device=<folder>&at=<UTC ISO-8601 instant, seconds, Z>`; no token, no other parameters. The browser session authorises.
- SceneTrove resolves the instant in the browser's local day (`localDay`, as the timeline rail does); covering clip = `start ≤ at ≤ end`; otherwise the first clip after `at` that day with a short notice; a missing device or day shows the notice and keeps the normal view. The `at`/`device` parameters are removed from the URL after use (replace).
- Vistoda options (EZVIZ only): `scenetrove_url` (empty = off; validated with `client_helpers.normalize_url`, http/https, no credentials/path/query) and `scenetrove_device` (default: the camera alias; `^[A-Za-z0-9_-]{1,64}$`).
- Info card: shown on the EZVIZ details page while `scenetrove_url` is empty, dismissible per browser (`localStorage` key `vistoda.scenetrove.card.dismissed`); text only (SceneTrove has no public page), IT and EN copy.
- Modal: with `scenetrove_url` set, the first action is "Apri in SceneTrove" (new tab, `rel="noopener"`); the existing play/download/save action stays below it.

## Review Focus

1. **Instant outside every clip** (gap, other day, before the first clip) → nearest later clip of that day with notice, or notice only. Test in Task 1 (`instant_in_a_gap_selects_the_next_clip_with_notice`).
2. **Unknown device in the link** → no crash, the current device stays, notice. Test in Task 1 (`unknown_device_keeps_the_current_one`).
3. **Malformed `at`** (not ISO, no zone) → ignored. Test in Task 1 (`malformed_instants_are_ignored`).
4. **SceneTrove URL with a trailing slash or a path** → normalized or refused. Test in Task 3 (`scenetrove_url_is_normalized_or_refused`).
5. **Link building escapes the device** → `encodeURIComponent`. Test in Task 4 (`scenetrove_links_are_escaped_and_utc`).

---

### Task 1: SceneTrove URL contract (pure)

**Files:** Create `scenetrove/ui/src/lib/instant-link.js`; Test `scenetrove/ui/tests/instantLink.test.mjs` (add to `test:unit` in `ui/package.json`).

**Interfaces — Produces:**
- `parseInstantLink(search: string) -> { device: string|null, at: number } | null` (`at` epoch ms; `null` when `at` is absent or not an ISO instant with zone).
- `resolveInstant(clips: Array<{id, start, end}>, atMs: number) -> { clipId: string|null, offsetSeconds: number, exact: boolean }` (clips of one day, ISO `start`/`end`).

- [ ] Steps: tests `malformed_instants_are_ignored`, `instant_inside_a_clip_seeks_into_it`, `instant_in_a_gap_selects_the_next_clip_with_notice` (`exact: false`), `unknown_device_keeps_the_current_one` (parse only returns the name; the controller checks membership) → RED (`node tests/instantLink.test.mjs`) → implement → GREEN → commit `feat(ui): parse and resolve instant links`.

### Task 2: SceneTrove applies the link once

**Files:** Modify `ui/src/lib/app-controller.svelte.js` (`loadDevices` ~197-216, `applyLoadedTimeline` ~217-230), `ui/src/lib/app-route-controller.svelte.js` (`updateUrl` replace to drop `device`/`at`), `ui/src/components/Viewer.svelte` (accept a one-shot `startOffset` consumed after the clip change effect at ~63-72), i18n strings (IT/EN) for the notice "Nessuna clip in questo momento: mostro la successiva." / "No clip at that moment: showing the next one." and "Dispositivo non trovato." / "Device not found.".
**Consumes:** Task 1.

- [ ] Steps: e2e or controller-level test where the repo allows (`tests/e2e/player-modes.spec.js` pattern) — `instant link opens the device, day and clip` — RED → implement (pending instant state: set at load, device switch via `selectDevice`, `setDeepLinkDay(localDay(at))`, after timeline load select `resolveInstant`, pass offset, then clear and replace URL) → GREEN → `ci-local --quick` → commit, push, watch CI and the SceneTrove deploy.

### Task 3: Vistoda options

**Files:** Modify `options_flow.py` (EZVIZ schema + `_scenetrove_options` validator next to `_event_archive_options`), `const.py` (`CONF_SCENETROVE_URL`, `CONF_SCENETROVE_DEVICE`), `strings.json`, `translations/{en,it}.json` (labels, descriptions, errors `invalid_scenetrove_url`, `invalid_scenetrove_device`); Test `tests/test_event_archive_options.py` (or a sibling file under 250 lines).

- [ ] Steps: tests `scenetrove_url_is_normalized_or_refused` (`https://st.example/` → `https://st.example`; `ftp://…`, `https://u:p@h`, `https://h/x?y` refused; empty clears), `scenetrove_device_defaults_to_the_alias` → RED → implement → GREEN → commit.

### Task 4: Panel metadata, info card, modal link

**Files:** Modify `panel_entry_metadata.py` (publish `scenetrove_url`, `scenetrove_device` for EZVIZ), `frontend/ezviz-alarm-model.js` (`sceneTroveLink(url, device, occurredAt) -> string|null`), `frontend/ezviz-alarm-dialog.js` (first action), `frontend/ezviz-alarms.js` (forward the two fields to `open()`), `frontend/ezviz-view.js` + new `frontend/scenetrove-card.js` (card on the details page), `panel-copy-ezviz.js`; Tests `tests/ezviz_alarm_model.mjs`, `tests/test_panel_entry_metadata*.py` (existing or new).

- [ ] Steps: tests `scenetrove_links_are_escaped_and_utc` (`sceneTroveLink("https://st.example","front door",1793214000)` → `https://st.example/?device=front%20door&at=2026-10-28T19%3A00%3A00Z`; null without url), metadata test → RED → implement → GREEN → browser check with local files (card visible without URL; button present with URL set on a test entry is not possible live → verify the link builder by test and the card live) → commit.

### Task 5: Release and verify

- [ ] Integration 0.49.0 (manifest/const/pyproject), all CI steps, tag, CI watched, homelab pin + deploy; set `scenetrove_url` on the front-door entry to `https://scenetrove.luigibarretta.com` and `scenetrove_device` to `spioncino` via the options flow API; browser check: the modal shows "Open in SceneTrove" and the link opens SceneTrove on spioncino at the event clip.
