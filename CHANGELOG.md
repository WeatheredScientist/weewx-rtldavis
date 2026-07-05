# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---

## [S27] — 2026-07-05 — Land the secret gate + collapse the review stack onto `dev`

Tied up the S23–S26 PR backlog (five open, nothing merged). No prod/driver code touched; all the
review work landed on `dev`, and `main` got only the secret gate.

- **Secret gate now blocking (P1).** Merged **PR #6 → `dev`** (`90ef51b`) and **PR #7 → `main`**
  (`490e776`) — `main` previously had zero secret scanning. CI on both merge commits: `secret-scan` =
  pass, `lint` = fail (expected pre-S24 ruff, non-blocking to the gate). Then set **`secret-scan` as a
  required status check** in branch protection on `dev` + `main` (via the keyring token — the PAT's 403
  was a scope problem; `enforce_admins: false`, no required reviews). The DEC-0012 gate is no longer
  advisory.
- **Governance/review stack collapsed onto `dev` (P2).** The whole stack merges clean — the predicted
  `ci.yml`/`check_secrets.sh` conflict never materialized because the stack's S20 gate fix (`2a6327c`)
  is byte-identical to dev's #6 fix. Retargeted **PR #5** (`feature/s24-code-quality-review`, whose tip
  already carried reception-dedup + s23-governance + s24/s25) to base `dev` and merged it (`2c75c5e`),
  bringing all S18–S26 work — the rain fix, reception Layer A, the S23 governance docs (LICENSE/AGENTS/
  ASSESSMENT), and the S24/S25 code-quality fixes — onto `dev` in one gated merge (secret-scan green,
  34/34 tests). Closed **#3** and **#4** as merged-via-#5.
- **S23 tail closed.** Folded the 8 still-open items from the retired root `cleanup_backlog.md` into
  `BACKLOG.md` (dedup'd against what it already carried) and deleted `cleanup_backlog.md` + the
  duplicated `logging.additions` fragment (`7025afa`).
- **`main` untouched beyond the gate.** The `dev`→`main` v2.0.3 promotion stays parked pending the rain
  fix's first wild glitch + the dewpoint rebuild.
- **Reception Layer A DEPLOYED live (DEC-0024).** scp'd the dev `weewx_monitor.py` to the NAS (backup
  `weewx_monitor.py.bak-20260705-141508`), `sudo kill`ed the monitor; the esynoscheduler `sleep 300`
  wrapper respawned it on the new code. **Confirmed**: the RF WINDOW metric dropped from a steady
  ~150–162% to **92%** (`22/24`) on the first post-restart window — same packet volume, correct
  epoch-dedup. Reversible via the backup.
- **Still owner/calendar actions (→ S28):** watch for the first real rain glitch; rotate the exposed WU
  key; the influxdb-grafana cherry-pick + stale-branch cleanup; remote-URL casing; set `STATION_NAME`
  in `monitor.env` (emails currently fall back to "My PWS").

## [S26] — 2026-07-05 — Fix the secret gate's mainline coverage (draft PRs #6 → dev, #7 → main)

A dashboard (dash) cross-repo note flagged the ported DEC-0012 secret gate as neutered and warned this
repo's gate "almost certainly has the same hole." Verified empirically — the concern is real, but not
where the note assumed. **No prod/driver code touched; two draft PRs, nothing merged.**

- **Diagnosis (empirical).** The neuter bug — the `grep -n` `<lineno>:` prefix matched the docstring
  allow-rule's bare `:` and silently whitelisted real `ident = secret` lines — was **already fixed** on
  the governance feature-stack in S20 (`2a6327c`, `:` → `[A-Za-z]:`); the current gate catches a planted
  secret assignment (a real-looking `api_key` value) that the old gate passed clean. But the fix
  never reached the mainline:
  - **`main`/`origin/main`** — **no `check_secrets.sh` and no `ci.yml` at all.** A fresh clone of the
    public default branch had zero secret scanning.
  - **`dev`/`origin/dev`** — the **neutered S17 gate**, *and* its secret-scan was the last step of a
    single CI job behind `ruff check`, which fails on the pre-S24 tree (32 errors) — so the whole job
    went red at ruff and the scan never ran. Doubly dead.
- **PR #6 → `dev`** (`s26-secret-gate-dev`) — replaced `check_secrets.sh` with the fixed version; split
  `.github/workflows/ci.yml` into an independent **`secret-scan`** job + a `lint` job so a lint failure
  can never skip the gate.
- **PR #7 → `main`** (`s26-secret-gate-main`) — added `check_secrets.sh` (fixed) + the two-job `ci.yml`
  + `.pre-commit-config.yaml` (main had none of the apparatus).
- **Verified.** On both PRs, CI **`secret-scan` = pass** (clean tree) and **`lint` = fail** (expected,
  pre-S24 ruff; non-blocking to the gate). Locally: planted secret caught (exit 1); the fixed gate scans
  each whole tracked tree clean (exit 0, no false positives).
- **Open (→ S27):** (1) mark **`secret-scan`** a **required** status check in branch protection on `dev`
  + `main` (needs repo admin; PAT 403'd) — until then CI is advisory, not blocking. (2) Reconcile the
  s20→s24 governance stack's old single-job `ci.yml` to this two-job structure when it merges. (3) Review
  + merge #6 then #7. Cross-repo finding recorded; the corrected takeaway for dash: verify against the
  branch that actually carries the fix, and confirm its own gate uses the `[A-Za-z]:` guard.

## [S25] — 2026-07-05 — Finish the S24 review fixes (on `feature/s24-code-quality-review`)

Completed the S24 review's deferred tail. **Branch-only, not deployed;** the driver changes still ride
the next rebuild + hot-swap. No-Rewrite honored — every change is surgical. Full offline suite green
(34/34: the prior 29 + 5 new `owm` tests).

- **U1/U2 (`owm.py` rebase)** — the uploader overrode `RESTThread.run_loop` with a hand-rolled
  `queue.get`/`urlopen` loop, silently discarding every resilience knob it was constructed with
  (`post_interval`/`max_backlog`/`stale`/`max_tries`/`retry_wait`/`skip_upload`) — a transient network
  failure dropped the record with no retry. Re-based on the standard hooks: kept `format_url`, moved the
  JSON body to `get_post_body(record) → (body, 'application/json')` (the same contract `influx.py`
  uses), deleted `run_loop`/broken `post_request`/`import time`/unused `urllib.request`. RESTThread now
  owns retry/backoff. New `tests/test_owm_post_body.py` (5 tests: kwargs forwarded, hooks not
  overridden, body shape + km/h→m/s conversion, None-field omission, appid URL).
- **U4 (`influx.py` TLS)** — `post_request` unconditionally used `ssl._create_unverified_context()` for
  any `https://` endpoint (silent MITM exposure). Added a `verify_ssl` option (**default `True`** =
  verifying context; explicit opt-out restores unverified for self-signed/internal endpoints), wired
  through the service `__init__` + `InfluxThread`, documented in the docstring. Moot for the current
  local `http://` Influx; drop-in.
- **M4 (dead code)** — deleted `_fmt` (py2-only `ord()`) and `parse_readings` from `rtldavis.py`; both
  had zero callers repo-wide.
- **L6 (driver nits)** — fixed the per-transmitter debug guard to test the list *element*
  (`stats['pct_good'][i] is not None`) instead of the always-truthy list; hoisted `_stderr_sample_count`
  init out of the hot read loop into `__init__`; annotated the unreachable `elif lines:` branch. **L5:**
  documented the `@staticmethod`-that-takes-`self` convention at `parse_raw` rather than restructuring.
- **Nit sweep** — `weewx_monitor.py`: narrowed three bare `except:` → `except OSError:`, and made the
  three hardcoded `/volume1/...` paths env-overridable (`WEEWX_RTLDAVIS_DIR`/`MONITOR_LOG`/
  `MONITOR_PIDFILE`/`WEEWX_LOG`) for parity with the env-sourced credentials. `windy.py`: replaced the
  `__import__('queue')` wart with a normal `import queue`. `influx.py __main__`: `os.environ[...]` →
  `.get(...)` so `--version`/`--help` no longer `KeyError`, and fixed the `InluxDfB` typos.
  `ogoxeUploader.py`: reconciled the contradictory `server_url` comments and logged the real
  hardcoded URL instead of `None`.
- **SPDX** — added per-file `SPDX-License-Identifier: GPL-3.0-or-later` headers to the driver + all
  reviewed satellites (`rtldavis`, `weewx_monitor`, `owm`, `windy`, `influx`, `ogoxeUploader`, `wcloud`,
  `loop_json_writer`).
- **Deferred (still, → S26):** **M-A** (monitor incremental read) and its coupled **L-B** (double-read
  race) — both wait for the DEC-0024 Layer A monitor deploy so they don't step on the queued
  `weewx_monitor.py`. The S24 driver fixes (H1/H2/M3) + these still need the rebuild/hot-swap.
- Verified: `py_compile` clean on all 8 touched modules; offline suite **34/34 green**; secret-scan
  passes on every changed file.

## [S24] — 2026-07-05 — Code-quality review + first fixes (on `feature/s24-code-quality-review`, stacked on S23)

Reviewed the driver and its satellites, then fixed the two real bugs plus the log-bloat source. **Fixes
are branch-only; the driver ones need a rebuild + hot-swap and are NOT deployed.** No-Rewrite honored —
every change is surgical.

- **`docs/CODE_REVIEW_S24.md` (new)** — deliverable-of-record: ranked findings across `rtldavis.py`
  (1506 ll), `weewx_monitor.py`, and all uploaders (`owm`/`windy`/`ogoxe`/`wcloud`/`influx`) +
  `loop_json_writer.py`. Draft **PR #5**, based on the S23 branch. Records a verification note: a
  candidate `setDaemon`/`setName` finding was **dropped** after testing against the live Python 3.14.5.
- **H1 (`0929952`)** — `parse_raw` unknown-channel branch referenced an undefined `raw` (param is
  `pkt`) → `NameError` inside `genLoopPackets` instead of the intended log line. One-line fix +
  `tests/test_parse_raw_channel.py` (proven to fail with the exact NameError pre-fix).
- **H2 (`970c47e`)** — `pct_good_all` bootstrap deadlock: `_update_summaries` only set it under a guard
  that also required it to be non-`None`, but `_init_stats`/`_reset_stats` null it every period, so the
  driver's own `rxCheckPercent` was **never populated** (likely why the log-scraping monitor exists).
  Dropped the self-defeating clause + `tests/test_reception_stats.py` (drives two archive periods +
  `new_archive_record`; fails pre-fix). Live-confirm `rxCheckPercent` on deploy.
- **M3 + U3 (`8872947`)** — the `weewx.log` bloat (DEC-0024 Layer B family): gated the driver's
  per-packet `RAW_CHANNEL_PAYLOAD`/`RAW_RTL_HOP`/`RAW_RTL_STDERR_SAMPLE` INFO logging behind
  `debug_rtld`, and dropped `influx.py`'s per-record `loginf` → `logdbg` (also fixed the "Bindding"
  typo). Pure log-level changes, no behavior change.
- **Deferred (in STATUS handoff → S25):** M-A (monitor incremental read — waits for the Layer A deploy
  to avoid stepping on it), U1/U2 (`owm.py` RESTThread rebase for retry/backoff), U4 (`influx.py` TLS
  verification), and the M4 dead-code + minor-nits + SPDX-header sweep.
- Verified: full offline suite **29/29 green** (H1 2, H2 2, plus the existing 25); secret-scan passes
  on every changed file; both edited modules `py_compile` clean.

## [S23] — 2026-07-05 — Cross-project governance alignment (on `feature/s23-governance-alignment`)

Docs-only, **no driver or prod code touched, not deployed.** Piloting a shared governance standard
across the three-repo Eagle Hunt family (this repo is the pilot; ASSESSMENT.md §2/§5).

- **`docs/ASSESSMENT.md` (new)** — cross-repo governance audit (weewx vs `eaglehunt-weather-dashboard`
  vs `hyperlocal-forecast`), the "isolate content / harmonize form" alignment model, a draft
  **Governance Standard v1** (shared core + per-repo profiles), ranked recommendations, and the
  pilot→harvest→propagate roadmap toward a generic project template.
- **`LICENSE` (new)** — GPLv3, verbatim canonical text (reused from `hyperlocal-forecast` for
  guaranteed-correct text + cross-repo consistency). Fills the gap of a public, published tool with no
  license; ecosystem-standard for a WeeWX-derived work. Per-file SPDX headers deferred to the S24 review.
- **`AGENTS.md` (new)** — cross-agent entrypoint (the `AGENTS.md` convention) pointing at CLAUDE.md +
  STATUS.md, so a non-Claude agent or human can pick the repo up from GitHub alone.
- **ROADMAP restructured** — shared `P0–P4` vocabulary mapped to short/medium/long horizons; folded to
  post-S22 reality with ✅ done-markers and a "vision" preamble; added the P0.5 governance-alignment
  workstream. P0 governance bootstrap marked done.
- **STATUS.md made the single source of truth** for the session number (DEC-0023) and the
  **next-session handoff moved into the repo** (out of Claude-private memory, now a pointer) — the
  north-star fix so handoff state is visible on GitHub. Doc-map reordered to put STATUS at slot #2.
- Verified: secret-scan gate (DEC-0012) passes on all changed files; docs-only diff.

## [S22] — 2026-07-05 — Merge PR #2 + reception metric Layer A fix (on `feature/reception-dedup`, off `feature/rain-spike-filter`)

Picked up the S21 handoff. No driver or prod code touched; not yet deployed.

- **Merged PR #2** (`s20-governance-hardening` → `feature/rain-spike-filter`): the S20 governance work
  (independent numbering DEC-0023 + two `check_secrets.sh` gate fixes) now rides with the rain fix
  toward v2.0.3. Resolved three append-conflicts keeping both S20 and S21 content (CHANGELOG S21→S20,
  DECISIONS DEC-0023 above DEC-0024, STATUS last-updated). Merge commit `1a265e7`.
- **Reception-metric Layer A fix (DEC-0024, `20bf7c0`):** `weewx_monitor.py` counted raw
  `Wunderground-RF … Published` log lines, but the driver publishes freqError freq-hop packets as
  duplicate publishes of the **same record epoch** — over-reading reception to ~150%. A live read-only
  sample (2026-07-05) showed a clean 2× (same `(epoch)` posted twice). Fix: a pure `wu_record_key()`
  helper dedups on the trailing `(<unix_epoch>)`; the window now counts **unique epochs**.
  `close_reception_window` + the driver are untouched. 6 offline tests
  (`tests/test_reception_dedup.py`). **Deploy = monitor restart only** (respawn loop reloads on-disk
  code); reversible. **Layer B stays deferred.**
- **Live read-only check (SSH):** confirmed no rain glitch has fired in the wild yet (v2.0.3 promotion
  still calendar-bound); verified the live `weewx_monitor.py` was byte-identical to the repo copy
  (md5 match) before patching.

## [S21] — 2026-07-04 — Reception metric ~150% root cause (DEC-0024) + numbering made independent (on `feature/rain-spike-filter`)

Investigation + governance, **no driver or prod code touched**. (The S20 governance-hardening
CHANGELOG entry rides in separately via draft PR #2 — see below.)

- **Reception-metric ~150% — root cause confirmed (DEC-0024, OPEN).** Live read-only diagnosis: the
  daily RF-Reception emails over-count because `weewx_monitor.py` counts `Wunderground-RF: Published`
  *log lines* ÷ `WU_RF_EXPECTED`(=24), but the driver publishes freqError freq-hop `CHANNELPacket`s as
  extra **dataless loop packets** (~1.66×; live sample 1605 publishes / 968 unique record epochs,
  single Transmitter:4). True reception was ~90%. Cosmetic — real weather data + the rain fix are
  unaffected. Documented Layer A (monitor counts unique epochs — safe, monitor-restart-only) vs
  Layer B (driver stops publishing dataless freqError packets + disable `RAW_*` debug logging; also
  fixes the 15 MB / 122 k-line `weewx.log` bloat). Fix **deferred** (diagnosis + docs only).
- **Doc-vs-reality flag:** BACKLOG claimed the Go binary emits no `ChannelIdx`/`FreqError`; the running
  binary emits **both** — the likely trigger. BACKLOG finding corrected.
- **Session numbering made independent per-repo (DEC-0023, supersedes DEC-0013).** A forensic audit
  showed the "shared lineage with the dashboard" premise never held (the dashboard runs its own
  continuous S1→S40 counter and never referenced a shared one). Each repo now counts its **own**
  sessions; number from *this repo's* CHANGELOG/STATUS +1; prefix cross-repo refs (`weewx S21` vs
  `dash S40`); this repo's line is contiguous S16→…→**S20**→**S21**. The prior draft PR that tried to
  *reunify* into a shared counter (mislabeled "S40") was reworked into the **S20** governance-hardening
  session and now rides as **draft PR #2** (`s20-governance-hardening`; PR #1 auto-closed by the branch
  rename). That branch also carries two real `check_secrets.sh` fixes.

## [S20] — 2026-07-04 — Governance hardening: independent session numbering + fix secret-scan gate (on `s40-governance-hardening`, off `feature/rain-spike-filter`)

Governance audit ("does our governance make sense, is it robust, is it aligned with the sibling
repos") + the fixes it surfaced. No driver/prod code touched.

- **Session numbering made independent (DEC-0023, supersedes DEC-0013):** a forensic audit showed the
  "shared lineage with the dashboard" premise never held — the dashboard runs its own continuous
  S1→S40 counter and never referenced a shared one; this repo's DEC-0013 invented a parallel counter
  that re-used numbers (S16–S19) the dashboard had long passed. Resolution: **each repo counts its own
  sessions**; number from *this repo's* own CHANGELOG/STATUS +1; prefix cross-repo refs (`weewx S20`
  vs `dash S40`). This repo's line stays contiguous **S16→S17→S18→S19→S20**. (An earlier draft of this
  session tried to *reunify* into the shared counter and relabel this session "S40"; reversed before
  merge so `main` never sees the detour.) Updated `CLAUDE.md`, `docs/STATUS.md`.
- **Secret-scan gate hardened (`scripts/check_secrets.sh`)** — the load-bearing DEC-0012 gate, two bugs:
  1. **False-negative (serious, latent since S17):** the generic assignment-style detector (branch b)
     was effectively **dead**. Its allow-list runs against `grep -n` output, and the docstring-param
     rule `:[[:space:]]*[A-Z][a-z]` matched the `<lineno>:` prefix (e.g. `1:api_key = "…"` → the `:a`),
     silently whitelisting virtually every real `ident = "secret"` line. Tightened to `[A-Za-z]:…`
     (require an alpha char before the colon) so the numeric prefix no longer matches. Verified: a
     planted fake credential (an `sk_live_…`-style token assignment) is now caught; the whole tracked
     tree still scans clean (no new false positives); genuine docstring params still allowed. (This
     very reword was itself flagged by the fixed gate — dogfooding. The S16 leaks were caught by the
     *identifier* branch, which skips this filter — so the hole went unnoticed.)
  2. **Empty-array crash:** threw `files[@]: unbound variable` under `set -u` when run by hand with no
     staged files (bash-3.2 empty-array expansion). Added a clean-pass guard so the manual whole-tree
     audit path fails safe. CI (`git ls-files | xargs`) and pre-commit were already unaffected by both.
- **Doc note (`docs/CONVENTIONS.md`):** the macOS dev box has only `python3` (no bare `python`); the
  prescribed `python -m …` validation commands don't run verbatim locally — noted, plus how to run
  the secret gate standalone.
- **Audit verdict:** governance is coherent and well-aligned with the dashboard's nine-file model
  (intentional, documented divergences: `INTERFACES.md` ← `DATA-MODEL.md`, added `BACKLOG.md`); the
  one real drift was STATUS.md going stale after the S18 deploy — already reconciled in `689b12c`.

## [S18] — 2026-07-04 — False-rain fix (on `feature/rain-spike-filter`, off `dev`)

Confirm-first diagnosis then fix for the phantom-rain bug. Not yet deployed (pending a dry-window
live hot-swap) or merged. Target release v2.0.3.

- **Diagnosis (read-only):** root cause confirmed from code + archive DB + driver logs — the driver
  treated *any* negative rain-counter delta as a 127→0 wraparound and added 128, converting an
  RF-decode glitch into phantom rain. Two events found in 63k archive records: 2026-05-25 (1.28",
  exceeds the world 1-min rainfall record) and 2026-07-04 (0.64"×2, `rain_count=-64` in the log),
  both flat-zero-bracketed and false vs the WeatherLink Live console. Corrected two prior
  assumptions: the counter is 7-bit (not 8-bit), and the recent event was −64→+64 (not a single +128).
- **Fix (`rtldavis.py`):** extracted the pure `rain_delta_tips()` helper (DEC-0021) — only near-−128
  deltas are wraparounds; small-negative and >60-tip (0.60") deltas → `None` (null-on-rejection,
  DEC-0006). Self-documenting docstring explains the bug for future readers.
- **Tests (`tests/test_rain_filter.py`):** 13 offline cases against the exact recorded signatures
  (both glitches reject; real −127 wraparounds and normal rain pass); stubs weewx so it runs with no
  install, wired for CI.
- **Backstop (`weewx.conf.example [StdQC]`):** `rain 0,10 → 0,1.0`; added `rainRate 0,16` — the
  live-config edit happens at deploy time.
- **Audit found (deferred to S19, DEC-0022):** `dewpoint_service.py` still substitutes stale
  temp/humidity/radiation/UV (DEC-0006 violation); minor windGust/radiation/UV StdQC gaps.
- **Email alert (`weewx_monitor.py`):** watch the weewx log for the driver's rejection line and
  email on each caught glitch (reusing the monitor's existing Gmail + log-tail; the driver stays
  pure I/O-free). Reports the counter values and the false rainfall the old code would have
  recorded. `--test-alert` sends a sample email for verification. Detection unit-tested
  (`tests/test_rain_glitch_alert.py`, 6 cases — no false positives on real wraparounds/uploads).
  DEPLOYED (rain driver + StdQC) to the live container 2026-07-04 via reversible hot-swap with an
  in-container import pre-flight; verified healthy. Monitor file staged; alert activates on the next
  monitor restart.

## [S17] — 2026-07-04 — Documentation governance bootstrap (on `dev`)

- Authored the nine-file governance package modeled on `eaglehunt-weather-dashboard` (DEC-0010):
  `CLAUDE.md` + `docs/{PRINCIPLES, CONVENTIONS, DECISIONS, ARCHITECTURE, INTERFACES, ROADMAP,
  STATUS}` + `CHANGELOG.md` + `BACKLOG.md`.
- `DECISIONS.md`: backfilled genesis ADRs DEC-0001…0009 (reconstructed, approximate dates) and
  recorded the governance-era decisions DEC-0010…0017 (governance model, branch model, secret
  hygiene, session numbering at S16, No-Rewrite, hyperlocal tooling graft, Opus 4.8 driver, and the
  interim gain-372 amendment).
- `INTERFACES.md`: documented the two consumer contracts — the loop-JSON real-time surface (field
  table + units + sparse-field caching) and the InfluxDB 2.x line-protocol schema — so the driver
  stays re-pointable toward non-Davis / CumulusMX producers (PRINCIPLES §1).
- Added Python tooling grafted from the hyperlocal-forecast repo (DEC-0015): `.pre-commit-config.yaml`
  (ruff, ruff-format, secret-scan) and `.github/workflows/ci.yml`.
- All authored on `dev`; `main` untouched.

## [S16] — 2026-07-04 — Reconcile repo with production reality → `prod-baseline-20260704`

The published repo had drifted badly from the live NAS system; the drift ran in *both* directions
(GitHub missing runtime files, but also GitHub *ahead* with corrupted uploaders). Captured what is
actually running as the truth on `main`. Commit `7e79d15`, tagged `prod-baseline-20260704`.

- **Added** runtime/driver files missing from the repo: `rtldavis.py` (the driver), `influx.py`,
  `loop_json_writer.py`, `ogoxeUploader.py`.
- **Fixed corrupted uploaders**: GitHub's `owm.py`/`windy.py` had stale duplicate class definitions
  appended that shadowed the clean RESTThread classes (Python uses the last definition) — a latent
  regression for anyone deploying from the public repo. Reconciled to the running versions.
- **Synced infra** stale v2.0.1 → live v2.0.2: `Dockerfile` (rtl-sdr pkg, `receiveWindow` patch,
  influx2 install, COPY steps) and `entrypoint.sh` (dropped syslogd, added `rtl_biast -b 1` bias-tee).
- **Regenerated `weewx.conf.example`** from the live config with maximum scrub (all credentials,
  station IDs, `station_url`, coordinates, and the InfluxDB org name → `YOUR_*` placeholders).
- **Curated `docker-compose.yml`** to driver-only; documented the hot-swappable extension mounts and
  treated downstream consumers (InfluxDB, dashboards) as external (DEC-0010, INTERFACES).
- **Expanded `.gitignore`** (secrets, backups, logs, data, dashboard artifacts, vendored deps).
- **Versioned `ops/`** RF/operational tooling under clean canonical names (dropped version-numbered
  sweep iterations); `wxcheck.sh` scrubbed of a hardcoded WU API key + PWS id.
- **Secret hygiene:** three real leaks caught and scrubbed pre-commit (a hardcoded WU API key + the
  PWS id in `wxcheck.sh`; a station-location chart title in `gain_sweep_analyze.py`; the InfluxDB
  org name). Verified the tracked tree carries zero personal identifiers.
- Resolved the four verify-at-start items: gain is live at **372** (not 207); the v2.0.3 dewpoint fix
  never shipped; the `rw250-test` Dockerfile exists (no reconstruction needed) but diverges toward
  rw350; live `weewx_monitor.py` matches GitHub.
- Discovered `v2.0.2` was never git-tagged (DEC-0003 gap); the vestigial `loopdata.py` mount.

---

## [Pre-S16] — pre-governance history (reconstructed, approximate)

- **v2.0.2** (~2026-05-31, built, never git-tagged): baked-in `rtldavis.py` windDir patch,
  `rtl_biast -b 1` bias-tee in `entrypoint.sh`, `rtl-sdr` package added.
- **v2.0.1** (~2026-05-29): RF reception monitoring in `weewx_monitor.py`, wind-filter iterations,
  elevation fix, StdCalibrate wind offset, STATION_NAME de-personalization.
- **v2.0-ubuntu26** (~2026-05-26): Ubuntu 26.04 / Python 3.14 multistage build (979 MB → 278 MB).
- **v1.0-ubuntu22** (~2026-05): original working image, Ubuntu 22 base.
- Extensive RF tuning (gain/fc/ppm/receiveWindow sweeps), the custom `loop_json_writer.py`, and the
  11-service upload chain were built across these sessions. See BACKLOG.md for the durable RF findings.
