# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---
## [S73] — 2026-08-11 — GATE 2 passed; the stall mechanism captured (zombie child); DEC-0080 applied; `:latest` → v2.0.12

- **Pilot night: 2 of 5 arms, then a stall-abort — and the abort is the session's biggest win.**
  P496 ran clean (75.56 %, n=33), P449 ran (72.65 %, n=15) until a **USB-stall killed it**: the
  01:52 forensics pre-capture shows `rtldavis` a **zombie** (`Z`, `wchan=do_exit`, zero fds, no
  replacement) — the child died mid-block and the driver neither reaped nor respawned it, so both
  USB resets were structurally futile (a device reset cannot resurrect a dead consumer). That is a
  **third mechanism**, neither of DEC-0075's two hypotheses. Three capture sets banked incl. an
  *effective* 23:56 reset (during the HLF/coffee-radar load spike, loadavg ~25) for contrast;
  reset #2 also hit a new **15 s sudo timeout** failure mode. Guard abort at 02:05 (30-min mean
  39 % — dead air, not reception; per-minute archive stayed ~72 %), tick raced it at the same
  second (no lock — minor apparatus defect, post-campaign fix), sticky STOP converged it safely.
- **GATE 2 (owner, Fable-escalated): arms {372, 496} confirmed** — 496 ≥ 449 answers the only
  question the pilot had to answer (curve not peaking below 449); missing low arms feed no
  decision the square doesn't make itself. **STOP cleared 08:55, H hold resumed, square runs
  08-12T00:05 → 08-20T00:05 unchanged.**
- **DEC-0080 APPLIED** — the exact-code radiation zero into the live `weewx.conf` **and**
  `weewx.conf.rx-baseline`, activated by the H-swap's own restart (zero extra downtime). The
  both-files requirement was a hazard found at apply: `restore_baseline` copies the snapshot over
  the live conf at every abort/campaign-end, so a live-only apply would have been silently wiped
  — BOOT's original apply steps missed it. Third `CONSTANTS.md` deviations row added. Dark-hours
  = 0 verification due tonight (S74). Ops note filed: dashboard `eh-ui.js` floor filter now
  vestigial.
- **`:latest` moved to v2.0.12 on Docker Hub** (GATE 2 decision): config digest `9db5c1…`
  verified byte-identical across both tags via the registry API; manifest digests differ
  (S70c save→load push vs S73 daemon push — compression, not content).
- **A second budget bug found and fixed the same morning (S57's lesson, one term deeper):** the
  08:55 H re-swap was aborted at 08:58:14 as "no records" while the driver was alive and
  publishing — `health_ok`'s 180 s budget never modeled **RF acquisition** (measured ~127 s on
  this boot vs ~0 s on P449's). First archive record was due ~08:58:15; the budget missed a
  healthy swap by seconds, and would have coin-flipped every square swap. `HEALTH_TRIES` 36 → 60
  (~300 s vs the corrected ~245 s worst case: boot 25 + rf-acquire 130 + interval 60 + lag 30);
  the regression test now asserts the four-term arithmetic. The 02:11 P402 abort likely shared
  this mechanism beneath the guard race (S74 confirms). Third abort email of the day is this one.
  Also fixed in passing: `test_current_schedule_is_installable_today` went red the morning the
  campaign legitimately launched (first row in the past ≠ stale) — renamed
  `…is_not_fully_stale`, asserting the **self-terminator** hasn't passed instead.
- **S74 staged as the stall deep-read** with a three-subagent read-only fan-out + frontier main
  thread (BOOT); S75 remedy candidates named (monitor auto-recreate re-opening DEC-0065, driver
  respawn fix, tick/guard lockfile). ROADMAP campaign-B/v2.0.12/USB-reset rows reconciled
  (DEC-0057, same session).

---
## [S72] — 2026-08-10 — DEC-0080: the diode-floor fix is decided — StdCalibrate exact-code zero, config layer

- **DEC-0080 — solar radiation diode-floor correction: option A** (escalated session, per the S71
  handoff's ask). One exact-window `StdCalibrate` line (`0 if 1.75 < radiation < 1.77`,
  None-guarded) zeroes the `sr_raw=1` dark-current code; added to `weewx.conf.example` as the
  versioned, public artifact — the anti-regression mechanism the June dashboard-only fix never
  had. Option B (almanac elevation-gated service) declined: it also needs a `process_services`
  live-config edit so it escapes no config fragility, it would bake one station's calibration into
  the public image, and its dawn/dusk benefit is below the sensor's own resolution — design
  preserved in the handoff, can ride the #144 rebuild if ever wanted.
- **NAS apply deliberately deferred to post-GATE 2** (unattended pilot tonight, no dongle
  recovery, config-typo crash-loop precedent) — apply steps + verification (incl. the `sr_raw=2`
  check) in `BOOT.md`.
- **PR #155 merged** (S71 close). **ops#148 closed on the tracker** — S71's commit subject said
  closed, but the explicit `gh issue close` was missed (CONVENTIONS' `Closes #N` lesson, adjacent
  form); closed with a pointer at S72 open.
- S69 + S68c–d rolled to `CHANGELOG-ARCHIVE.md` verbatim (~3-session window). `MANIFEST.md`
  handoffs row de-counted (a literal "three" had gone stale). Green gates clean on pickup (ruff,
  185 tests, mypy 39 files).

---
## [S71] — 2026-08-10 — ops#148/#7 closed; ERR-0005 backfilled; solar diode-floor traced and designed

- **ops#148 closed.** `MANIFEST.md`'s `CHANGES-FROM-UPSTREAM.md` row widened to name all 9
  uncovered files — it already documents each one's provenance (4 vendored forks, 5 original), so
  this was a one-line widen, not a new row. Verified against the sweep's own bare-filename matching.
- **DEC-0079 — opted into `.claude/transient-state` (ops#113).** Tracked file created (force-added
  past the local `.git/info/exclude`, same precedent as `settings.json`), convention documented in
  `CONVENTIONS.md`. Left empty — no current state meets the motivating shape that isn't already
  prominent in `BOOT.md`.
- **`BOOT.md` ordered backlog resequenced:** `#144` (console pressure / `pressure_service.py` field
  collision) then `ops#141` (HLF archive-directory mount) queued for after GATE 2, each flagged with
  why it's design work rather than mechanical execution.
- **ERR-0005 backfilled.** 7 records at `interval=15` inserted into the archive (backed up first:
  `weewx.sdb.bak-S71-preBackfill-20260810-124656`), daily summary rebuilt, matching InfluxDB points
  written flagged `backfill=1.0`. **Both machine history APIs failed first** — WU's `v2/pws/history/all`
  401'd, WeatherLink v2's `v2/historic/{id}` (same credentials `pressure_service.py` uses hourly)
  returned an empty `{}` with a 200 — neither carries historical-read entitlement on this account.
  Sourced from a manual WeatherLink/WU website read instead; recorded in `DATA_ERRATA.md` so a future
  backfill skips straight to that.
- **Solar radiation diode-floor bias — diagnosed, fix designed, not yet applied.** Owner recalled a
  prior fix; traced via the owner's own claude.ai search (this repo's git history and archive both
  start 2026-05-19, so nothing here predates it) to a June 2026 dashboard-only presentation-layer
  filter. Verified against the *current* dashboard: still correct for live numeric displays, but the
  24h chart panel (`eh-charts.js`) queries InfluxDB raw with no filter — regressed during the
  dashboard's July supercard refactor, the second time a per-path filter has been dropped on
  refactor. Decision: fix at the source here instead of patching the dashboard a third time. Two
  designs drafted and compared (`StdCalibrate` magnitude-match vs. a `weewx.almanac`-based
  elevation-gated service); full brief for the next session in
  [`docs/handoffs/S71-radiation-floor-design.md`](docs/handoffs/S71-radiation-floor-design.md).
- Green gate re-run clean throughout (185 tests).

---
## [S70] — 2026-08-10 — v2.0.12 promoted and built; campaign B GO, first launch night scrubbed on a dead VPN

- **Campaign B: GO.** Assessed against DEC-0066's hold: both gates closed on measurement
  (DEC-0069/0070), campaign A uncontaminated (DEC-0077) — the "instrument trusted" condition is
  met. The swap-night constraint is moot: the LNA has been out since 08-02, so the launch is a
  container swap + install, all remote.
- **Release v2.0.12 promoted** (PR #151): dev → main, `main` = `7b6fd42`. Image delta vs v2.0.11
  is four baked files (BIAS_TEE env, DEC-0062 redaction, driver stderr drain + ws.4 bump) —
  observability only, pre-registered as the one-image-for-B plan (DEC-0064).
- **The arm64 laptop can no longer build this image** — `docker build --platform linux/amd64`
  dies in tar with `Function not implemented` (ENOSYS under emulation), and the failure hid
  behind a `| tail` pipeline exit 0 until the log was read (the green-checkmark trap, again).
  Built **natively on the NAS** instead (v2.0.3 precedent): `9db5c1ddaac3`, verified by an
  explicit `BUILD-EXIT=0` marker. Hub push deferred (docker save → laptop → push from a home
  network); `:latest` waits for prod proof.
- **The 08-09 launch night was scrubbed at 00:58** — the VPN dropped end-to-end (ppp0 gone,
  route fell back to the foreign LAN's gateway) with the 00:35 first pilot row already passed.
  The runbook's postpone-24h contingency, exercised as designed: prod untouched, campaign A's
  script + STOP sentinel still in place, nothing half-deployed. Schedule regenerated +1 day
  (39 rows, S62's constant-offset method): **pilot 08-11T00:35, square 08-12 → 08-20T00:05**.
- No stall overnight (blocker 4 still waiting); prod healthy through the NAS build (v2.0.11,
  Up 4 days).
- **Deploy executed 08-10 morning, campaign B ARMED.** Campaign A archived (five artifacts →
  `.campaignA`, including the root-owned STOP sentinel the runbook's list omitted — a tick
  refuses while it exists); B's `rx_experiment.sh` deployed from merged tip `b7a07e1` and
  sha-verified (`6a99c949`); container swapped in one nohup'd batch (VPN-drop-safe after the
  previous night's lesson), `SWAP-EXIT=0`. Verified in the running system per DEC-0046: ws.4
  banner, `Bias-tee disabled (BIAS_TEE=0)` line, DEC-0062 redaction line, loop-JSON advancing,
  reception 70% → 57/59% through the swap dip → **70% [OK]** recovered. `install` clean at
  09:40: baseline snapshotted, **pilot 08-11T00:35, square 08-12 → 08-20T00:05**. Soak with the
  new expectations: **16 pass / 1 warn (settling reception) / 0 fail**.
- **DEC-0078 — image builds move to the NAS.** The laptop failure above is deterministic, so the
  NAS-native path is now the release mechanic, with Hub publication decoupled (`save` → laptop →
  `push`, only after prod proof — Hub lags prod until pushed, documented in CONSTANTS). CI
  builds noted as the structural fix, backlogged. `EXPECT_*` flipped to v2.0.12/ws.4 in the same
  deploy; ROADMAP P2 reconciled (DEC-0057): release item closed, campaign B item now LAUNCHED.
- **`:v2.0.12` pushed to Docker Hub at S70 close, digest-verified end to end:** the Hub
  manifest's config digest is the NAS build id (`9db5c1…`) — what the public pulls is provably
  what prod runs. One recorded blemish: the save→load→push path re-pushed the layers
  near-uncompressed (283 MB vs ~120 MB typical; same 8 layers, each ~2.2×) — content-identical,
  harmless, tightening deferred to DEC-0078's CI-build follow-up. `:latest` deliberately still
  v2.0.11 until the station proves the release (GATE 2). ops#152 closed on the measured green
  sweep.

---
