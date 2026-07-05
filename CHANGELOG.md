# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---

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
