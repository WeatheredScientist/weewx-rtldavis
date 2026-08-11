# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---
## [S74] — 2026-08-11 — Day's second guard abort root-caused and cleared; square proceeds on schedule

- **09:55 guard abort root-caused**: reconstructed the exact 6-sample mean from `weewx_monitor.log`
  (70/30/70/71/20/16 → 46), matching `30-min mean reception 46% < 50% floor (arm H)` exactly. Traced
  to an RF-dead episode 09:33–10:04 (pre-ws.5): USB reset attempted and logged **ineffective**,
  recovery uncorrelated with the reset — the DEC-0081 signature, not a new failure mode. STOP
  cleared (owner-confirmed in chat, Class C mint); verified stable through a second live episode
  (17:52–17:59, also self-recovered, also non-mute) without re-tripping. Square proceeds on
  schedule, 08-12T00:05.
- **Monitor respawn and `dev`→`main` promotion confirmed** (both landed before this session's
  investigation, likely the concurrent session): pid 22206 (was 8810), `Monitor started` 15:29:02;
  PR #161 merged, `prod-baseline-20260811` tagged.
- **`ops/soak_check.sh` run: 14 pass / 2 warn / 1 FAIL** — repeated rtldavis stalls (2, both
  post-ws.5, both non-mute RF-class, both self-recovered <7 min). Frequency is a new, unexplained
  data point for DEC-0081's still-open characterization, not itself a regression.
- **Condensation floated as a fourth DEC-0081 candidate cause** (interference / no-LNA margin /
  site / condensation) — plausible for the one overnight episode, doesn't explain the two daytime
  ones. Unconfirmed either way.
- **Dependabot PR #158 (weewx 5.4.0→5.5.0) reconfirmed deliberately deferred** post-campaign; its
  `tests` check is also currently failing regardless of timing.
- DEC-0080 dark-hours (radiation=0) verification **still pending** — S74 found the correction live
  but dark hours hadn't happened yet at check time; carried to S75.

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
- **The stall deep-read ran the same afternoon (owner pulled it forward) and re-diagnosed the
  class — DEC-0081.** Three read-only subagents (capture collation / night timeline / HLF +
  coffee-radar cross-correlation) + main-thread differential against the driver source: the
  device never re-enumerates, the driver's watchdog and respawns work, and the stalls are
  **RF-dead episodes** — resets are theater (~17 attempts, 0 fixes), ERR-0005's recreate-fix
  reads as episode-end coincidence, DEC-0065 vindicated. The first-draft remedy
  (auto-kill+start) was **rejected by its own differential** — restarts show the same
  evidence pattern as resets — and replaced with: reset demotion (`RESET_MAX_TRIES` 3→1),
  driver child-reaping (three stacked zombies captured; the one real process bug),
  `STALL DIAGNOSIS` / `DATA DROUGHT` self-classification, and the `episodes.log` ledger as
  the pre-registered LNA-verdict datum (owner reports for ~50–70 m/trees/walls sites).
- **v2.0.13 / ws.5 shipped same day, mid-H-hold, before the square's first block** (PR #159,
  merged tip `1530971`): NAS build `BUILD-EXIT=0`, container swap with identical
  mounts/devices/env + `BIAS_TEE=0`, ws.5 banner + DEC-0031 canary verified live, records in
  35 s, soak 15/2/0 after the ineffective-reset criterion reframe (FAIL→WARN — a criterion
  failing on now-expected behavior is the ops#147 item-6 anti-pattern). `:v2.0.13` on Hub;
  `:latest` holds at v2.0.12 until proven. Monitor deployed + sha-verified; respawn pends the
  owner's path-scoped-sudo kill (uid-1031 process — the day's one genuinely owner-run step).
  Tests 185 → 203 (+18: reap, diagnosis/drought, ledger; escalation test re-pinned to the
  single-hedge policy). CHANGES-FROM-UPSTREAM rows 12–13 (both upstreamable). Dependabot
  PR #158 (weewx 5.4.0→5.5.0) deliberately left open — no base-platform bump mid-campaign.
  ROADMAP campaign-B/v2.0.12/USB-reset rows reconciled (DEC-0057, same session).

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

*(S71, S70 rolled to `CHANGELOG-ARCHIVE.md` verbatim — the ~3-session window.)*
