# Phase 1: user-set alarm retention — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the user set how many alarms per camera (50–2000) and how much
picture storage (64–2048 MiB) the Vistoda EZVIZ app keeps, with clear
disclaimers.

**Architecture:** Two new app options in the catalog map to two bridge
environment variables. The bridge reads them with clamping, and the alarm
store uses them instead of the compile-time `MAX_EVENTS` and
`TOTAL_PICTURE_BYTES`. An id index keeps duplicate checks cheap at 2000
alarms.

**Tech Stack:** Rust 1.88 (bridge, `ezviz-vtm-bridge`), Bash + jq (app entry
`run.sh`), Home Assistant app catalog YAML.

**Spec:** `docs/superpowers/specs/2026-10-29-event-archive-and-scenetrove-link-design.md`,
section 1 (phases 2–4 get their own plans after this one ships).

## Global Constraints

- Ranges and defaults are exact: `alarm_history_limit` int 50–2000, default 200;
  `alarm_picture_budget_mib` int 64–2048, default 256 (all cameras together).
- Env names are exact: `EZVIZ_BRIDGE_ALARM_HISTORY_LIMIT`,
  `EZVIZ_BRIDGE_ALARM_PICTURE_BUDGET_MIB`.
- Out-of-range or non-integer env values → clamp (or default) and log one
  warning; never fail startup.
- Lowering the limit trims the oldest alarms and their pictures at the next start.
- Disclaimer copy in IT and EN (Task 3) is fixed by this plan.
- `vistoda-ezviz`: LOC budget 250 per maintained file; run
  `node third_party/repo-tooling/ci-local.mjs` (all 9 steps) before pushing,
  through the build lock (`PATH=$HOME/.local/dev-build-lock-bin:$HOME/.cargo/bin:$PATH`).
- Git in these repos needs `GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=safe.directory GIT_CONFIG_VALUE_0='*'`.
- Release chain: bridge tag `v0.17.0` → ghcr image → `vistoda-addons` catalog
  `0.4.47` (tag, signed release evidence) → homelab pins → `deploy-ha-media-bridge`.

## Review Focus

1. **Limit lowered from 2000 to 50 with a full store.** Next start keeps the 50 newest, deletes the other pictures, and the poller does not re-insert the evicted alarms as new. Tests in Task 2 (`lowering_the_limit_trims_at_load` and `evicted_alarms_are_not_reinserted`).
2. **Unset options on an existing install** (catalog older than 0.4.47, or `options.json` without the keys) → defaults 200 / 256, no startup failure. Tests in Task 1 (`missing_or_invalid_values_use_defaults`) and Task 3 (`jq` defaults in `run.sh`).
3. **Many cameras.** The picture budget is split per camera as today (`budget / cameras`). Test in Task 2 (`picture_budget_is_split_per_camera`).
4. **Duplicate check at 2000 alarms** stays correct after eviction and reload: the index drops evicted ids. Test in Task 2 (`index_follows_eviction_and_reload`).
5. **Env value `0`, negative or huge** → clamped, warning logged once. Test in Task 1 (`out_of_range_values_are_clamped`).

---

### Task 1: Bridge config reads the two limits (vistoda-ezviz)

**Files:**
- Modify: `src/config.rs` (struct `BridgeConfig`, `from_env`, new helper, tests module)
- Modify: `README.md:160` area and `docs/OPERATIONS.md:103` area (env table/prose)

**Interfaces:**
- Produces: `BridgeConfig.alarm_history_limit: usize`, `BridgeConfig.alarm_picture_budget_bytes: u64`;
  `fn clamped(name: &str, default: u64, minimum: u64, maximum: u64) -> u64` (private).

- [ ] **Step 1: Write the failing tests** in `src/config.rs` `mod tests` (env set/unset through the existing test pattern there):

```rust
#[test]
fn missing_or_invalid_values_use_defaults() {
    // unset → 200 / 256 MiB; "abc" → default
    assert_eq!(clamped("EZVIZ_BRIDGE_ALARM_HISTORY_LIMIT", 200, 50, 2000), 200);
}
#[test]
fn out_of_range_values_are_clamped() {
    // "0" → 50, "999999" → 2000; MiB "1" → 64, "100000" → 2048
}
```

- [ ] **Step 2:** `cargo test --locked --lib config` → FAIL (`clamped` undefined).
- [ ] **Step 3:** Implement `clamped` (parse `u64`; non-integer → default; outside range → nearest bound; `tracing::warn!` with the name and the applied value). Add the two fields: `alarm_history_limit = clamped(..._HISTORY_LIMIT, 200, 50, 2000)` as `usize`; `alarm_picture_budget_bytes = clamped(..._PICTURE_BUDGET_MIB, 256, 64, 2048) * 1024 * 1024`. Document both env vars next to `EZVIZ_BRIDGE_ALARM_POLL_SECONDS` in README and OPERATIONS.
- [ ] **Step 4:** `cargo test --locked --lib config` → PASS.
- [ ] **Step 5:** Commit `feat(config): user-set alarm history limit and picture budget`.

### Task 2: Alarm store uses the runtime limits (vistoda-ezviz)

**Files:**
- Modify: `src/alarms/store.rs` (`CameraHistory` fields, `load`, `push`, `knows`, `insert`)
- Modify: `src/alarms/mod.rs` (`AlarmFeed::load`, `TOTAL_PICTURE_BYTES`, re-export)
- Modify: `src/alarms/poller/support.rs:23` (`recent(MAX_EVENTS)`)
- Modify: `src/api.rs:102-106` (pass the config values)
- Test: `src/alarms/tests/feed.rs`, `src/alarms/tests/poller.rs:79`

**Interfaces:**
- Consumes: `BridgeConfig.alarm_history_limit`, `BridgeConfig.alarm_picture_budget_bytes` (Task 1).
- Produces: `pub struct AlarmLimits { pub history: usize, pub picture_bytes: u64 }` in `alarms/mod.rs` with `Default` = 200 / 256 MiB;
  `AlarmFeed::load(directory, cameras, metrics, limits: AlarmLimits) -> Arc<Self>`;
  `CameraHistory::load(directory, camera, picture_budget: u64, limit: usize) -> Self`;
  `CameraHistory::limit(&self) -> usize`. `MAX_EVENTS` is renamed `DEFAULT_HISTORY_LIMIT` (200).

- [ ] **Step 1: Write the failing tests** in `src/alarms/tests/feed.rs`:

```rust
#[test] fn lowering_the_limit_trims_at_load()      // insert 5 with limit 5, reload with limit 2 → sequences of the 2 newest; evicted pictures removed from disk
#[test] fn evicted_alarms_are_not_reinserted()     // limit 2, store full; insert a record older than the oldest retained → outcome.inserted == 0
#[test] fn index_follows_eviction_and_reload()     // limit 2; insert a,b,c → knows("a") == false, knows("c") == true; reload → same
#[test] fn picture_budget_is_split_per_camera()    // AlarmFeed::load with 2 cameras and picture_bytes 64 MiB → each history budget 32 MiB (assert via a store accessor or a picture eviction case)
```

- [ ] **Step 2:** `cargo test --locked --lib alarms::tests` → FAIL (signatures).
- [ ] **Step 3:** Implement:
  - `CameraHistory` gains `limit: usize` and `index: HashSet<String>`; `push` inserts into the index and evicts beyond `limit` (removing the id and picture); `knows` uses the index; `load` skips to the newest `limit` records.
  - `insert` skips a record when the store holds `limit` alarms and the record's `occurred_at` is older than the oldest retained one.
  - `AlarmFeed::load` splits `limits.picture_bytes` per camera as today and passes `limits.history`.
  - `poller/support.rs` uses `history.recent(history.limit())`.
  - `api.rs` builds `AlarmLimits` from the config. Test helpers call `AlarmLimits::default()`.
  - Keep `store.rs` ≤ 250 lines (move code to `store_read.rs` if needed).
- [ ] **Step 4:** `cargo test --locked --lib alarms` → PASS.
- [ ] **Step 5:** Commit `feat(alarms): runtime history limit with an id index`.

### Task 3: App entry, version and release of the bridge (vistoda-ezviz)

**Files:**
- Modify: `packaging/home-assistant/run.sh` (exports before `vistoda_start_child`)
- Modify: `Cargo.toml`, `Cargo.lock`, `Dockerfile`, `packaging/home-assistant/Dockerfile` (0.16.0 → 0.17.0)

- [ ] **Step 1:** In `run.sh`, next to the other exports:

```bash
export EZVIZ_BRIDGE_ALARM_HISTORY_LIMIT="$(jq -r '.alarm_history_limit // 200' "${options_file}")"
export EZVIZ_BRIDGE_ALARM_PICTURE_BUDGET_MIB="$(jq -r '.alarm_picture_budget_mib // 256' "${options_file}")"
```

- [ ] **Step 2:** Bump the version to 0.17.0 in the four files.
- [ ] **Step 3:** Full gate: `node third_party/repo-tooling/ci-local.mjs` → "all 9 step(s) passed".
- [ ] **Step 4:** Commit `feat(app): alarm retention options (0.17.0)`, tag `v0.17.0`, push `main` and the tag; wait for `ghcr.io/luigibarretta/vistoda-ezviz-addon:0.17.0`.

### Task 4: Catalog options with disclaimers (vistoda-addons)

**Files:**
- Modify: `vistoda_ezviz/config.yaml` (`version`, `options`, `schema`)
- Modify: `vistoda_ezviz/translations/it.yaml`, `vistoda_ezviz/translations/en.yaml`
- Modify: `vistoda_ezviz/DOCS.md`, `vistoda_ezviz/CHANGELOG.md`, `VERSION` (0.4.47), `COMPATIBILITY.md`, `scripts/check.py` (`"vistoda_ezviz": "0.17.0"`)

- [ ] **Step 1:** `options`: `alarm_history_limit: 200`, `alarm_picture_budget_mib: 256`; `schema`: `int(50,2000)`, `int(64,2048)`; `version: 0.17.0`.
- [ ] **Step 2:** Translations (exact copy):
  - it `alarm_history_limit` — name: "Eventi conservati per telecamera"; description: "Quanti eventi tenere per ogni telecamera (50–2000). Eventi e immagini stanno sul disco di Home Assistant e finiscono nei suoi backup. Per uno storico lungo usa l'archivio eventi di Vistoda su un'unità di rete, oppure SceneTrove. Se abbassi il valore, gli eventi più vecchi vengono eliminati al prossimo avvio."
  - it `alarm_picture_budget_mib` — name: "Spazio massimo per le immagini (MiB)"; description: "Spazio totale per le immagini degli eventi di tutte le telecamere (64–2048 MiB), diviso in parti uguali. Quando è pieno vengono eliminate le immagini più vecchie insieme ai loro eventi. Conta anche nella dimensione dei backup di Home Assistant."
  - en `alarm_history_limit` — name: "Events kept per camera"; description: "How many events to keep for each camera (50–2000). Events and pictures are stored on Home Assistant's own disk and included in its backups. For a long history use the Vistoda event archive on network storage, or SceneTrove. Lowering the value deletes the oldest events at the next start."
  - en `alarm_picture_budget_mib` — name: "Maximum picture storage (MiB)"; description: "Total space for event pictures of all cameras (64–2048 MiB), split evenly. When full, the oldest pictures are deleted together with their events. It also counts towards the size of Home Assistant backups."
- [ ] **Step 3:** DOCS.md: a short "Storico eventi" section repeating the disclaimer; CHANGELOG `## 0.17.0` ("Puoi scegliere quanti eventi conservare e quanto spazio usare per le immagini.").
- [ ] **Step 4:** `python3 -I scripts/check.py` → "Vistoda Apps repository contracts passed".
- [ ] **Step 5:** Commit `Release EZVIZ 0.17.0 in catalog 0.4.47`, tag `v0.4.47`, push; wait for `release-evidence.json` of `v0.4.47` on GitHub listing 0.17.0.

### Task 5: Deploy and verify on iot-01 (homelab-ansible)

**Files:**
- Modify: `inventory/host_vars/it1-prd-iot-01.yml` (`ha_vistoda_ezviz_app_version: 0.17.0`, `ha_vistoda_app_catalog_version: 0.4.47`)
- Modify: `tests/test_vistoda_deploy.py` (`ha_vistoda_ezviz_app_version: 0.17.0`)

- [ ] **Step 1:** `cd tests && python3 -m unittest test_vistoda_deploy` → OK.
- [ ] **Step 2:** Commit `vistoda: pin EZVIZ app 0.17.0 and catalog 0.4.47`, push.
- [ ] **Step 3:** `ansible-playbook -i inventory/hosts.ini playbooks/deploy-ha-media-bridge.yml` → recap `failed=0`.
- [ ] **Step 4:** Verify: `curl http://192.168.50.140:8765/healthz` → `"version":"0.17.0"`; `ha apps info 10aad50a_vistoda_ezviz` options include `alarm_history_limit: 200` and `alarm_picture_budget_mib: 256`; the alarm feed still returns the same events as before the deploy (`GET /v1/cameras/front-door/alarms` count unchanged).
