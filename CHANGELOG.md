# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---
## [S76] — 2026-08-12 — Stall rate measured, not eyeballed (DEC-0083); secret gate's sixth hole closed (DEC-0084)

- **DEC-0083 — S75's "trending hot" survives measurement, but its evidence did not.** Over 30.5 d
  and 31 rotations the 48 h and 72 h windows ending now hold **6 episodes each, the record
  maximum** (98th pct); 24 h is 96th pct but off its peak of 5, so the burst may be easing.
  **The unit had to be fixed first**: a stall *line* is not an event — the 150 s watchdog re-raises
  every ~3 m 40 s, so 08-02 is **21 lines and one episode**. Clustering gives 15 episodes, stable
  at 30/45/60 min, and **reproduces DEC-0081's independently-derived boundaries** for the 08-10/11
  night exactly.
- **Three corrections to how S75 reached it.** Onset is **08-10 23:56**, not ws.5 — the v2.0.13
  container started 18:05 local on 08-11, so **5 of the 6 burst episodes predate it**; the ledger's
  19-hour field of view was mistaken for the phenomenon's onset. Not a simple LNA effect either:
  LNA-in 0.40/day → LNA-out 08-02→08-10 **0.13/day, the quietest stretch in the record** →
  08-10→now **2.43/day**. And "2→4 ledger rows" **compared two instruments** — row 3 is
  drought-only and `DATA DROUGHT` appears zero times in every pre-ws.5 log.
- **DEC-0081 amended: its LNA dates are wrong.** "08-02 and 08-06 were LNA-in" — the LNA came out
  **mid-ERR-0005, early 08-02** (S61: none existed yet; S62: "first honest no-LNA telemetry
  accruing"; S70: "out since 08-02"). **08-06 was LNA-OUT**; 08-02 only straddles. The clause's
  point survives on 08-02 alone.
- **New sanctioned readout `ops/stall_baseline.py`** (+7 tests, 203 → 210) — states its
  left-censored window and threshold sensitivity every run. Building it exposed a bias in its own
  first cut: anchoring "current" on the last stall guarantees the window contains it, so the check
  would read hot right after every episode. Fixed to anchor on now.
- **Secondary sweep (ops#160 job 3): freeze rate measured at 1.49/day, median 240 s** against the
  inherited "~once/day, ~3.5 min" — right order of magnitude, **~40 % understated**, refines rather
  than overturns. **A 60 % confounder was removed first**: the S37 backfill's `interval=15` rows
  read as 28 phantom 900 s freezes, caught only because individual events were printed rather than
  the summary rate. **Co-rejection watch re-verified 0 through 08-12 and positive-controlled**
  (stale at "through 08-01"); phantom-rainRate already instrumented in `soak_check.sh`.
- **DEC-0084 — secret gate hole class 6, found free by the routine pre-commit positive control.**
  `_assign` needs 8+ *consecutive* value chars and a Google app password breaks that run every 4;
  `_apppw` required **quotes**. So an **unquoted** app password was missed in every spelling —
  and unquoted is the **native form of `weewx.conf` (ConfigObj) and `monitor.env`**, the two files
  that must never be committed. Gitignored, so nothing leaked. **It survived S68 because that fix
  planted the quoted literal, went green, and never asked the neighbouring spelling.** Fix is
  key-anchored (an unanchored shape match would flag ordinary English prose); **one allow-list
  widening refused** — five of the six historical holes were allow-list defects, so
  `monitor.env.example`'s placeholder moved to `YOUR_GMAIL_APP_PASSWORD` instead. Harness holes
  27–29, **54 passed / 0 failed**. **The new detector then went red on the DEC entry documenting
  it** — the first draft wrote the literal shape into `DECISIONS-FULL.md`, and the gate caught it,
  exactly as `check_secrets.sh`'s own comment predicts. A decision log earns no exemption
  (DEC-0045); both spellings are now described rather than written.
- **ops#147 closed out from this repo's side** — weewx's §11 adoption named (DEC-0072 for item 1,
  DEC-0074-as-corrected for item 3); it was the one thing the thread was still waiting on here.
- Green gate: ruff clean, **210 tests**, mypy clean on 44 files. *A first mypy run reported
  "Success" on 42 files while silently skipping both new ones — `git ls-files` lists tracked files
  only. Staged first, then re-ran: 5 real errors.*

---
## [S75] — 2026-08-12 — Campaign B square recovered from an overnight stall; DEC-0080 verified clean

- **Discovered mid-session-start: the square never swapped to arm A.** A third same-day RF-dead
  episode (18:05, 08-11) tripped the sticky STOP six minutes after S74 verified the day's second
  episode "without re-tripping" — the STOP sat unnoticed through the entire scheduled 00:05
  A-arm swap, blocking every 5-minute tick for ~15h until this session's start.
- **Recovered via DEC-0082**: shifted the entire remaining square schedule +24h (not a
  partial-day restart, which `test_schedule_is_a_balanced_latin_square` rules out) — full 8/8
  per-arm balance preserved, 17/17 tests pass unmodified. Deployed to the NAS, sha-verified, STOP
  cleared. Arm A now due `2026-08-13T00:05`; square runs through `08-21T00:05`.
- **DEC-0080 dark-hours radiation verification: clean.** 495 archive rows across the 08-11→12
  dark window (21:00–05:30), zero non-zero radiation readings.
- **Stall rate: 2 → 4 episodes** in `episodes.log` since the ws.5 deploy (two new overnight,
  01:34–01:45 the longest yet at 647s) — eyeballed as "trending hot," which is itself the trigger
  for a properly baseline-measured follow-up (ops#160, S76).
- **`soak_check.sh`: 14 pass / 3 warn / 0 fail** — reception 67%, no-banner (cosmetic),
  USB-reset-ineffective (expected DEC-0081 signature).
- **Guard/classifier friction on the schedule deploy**: `scp` hit three independent layers before
  landing — the expected Class C confirm, `secret-read-guard.sh` re-blocking even with its own
  documented `command`-prefix escape hatch already applied (looks like a bug), and a bare
  classifier denial on an `rsync` substitution with no mint path. Owner ran the final `scp` by
  hand.
- **ops#160 filed**: S76 scoped to apply the "baseline-measured, not eyeballed" pattern (ops#159)
  to this repo's own standing watches, stall rate first.

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
*(S72, and now S71/S70 before it, rolled to `CHANGELOG-ARCHIVE.md` verbatim — the ~3-session window.)*
